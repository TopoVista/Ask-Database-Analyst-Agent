"""Workspace-isolated immutable snapshot storage adapters."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ObjectMetadata:
    key: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class AttemptMetadata:
    prefix: str
    modified_at: datetime


class SnapshotStore(Protocol):
    def put(self, workspace_id: UUID, key: str, body: bytes) -> ObjectMetadata: ...
    def put_file(self, workspace_id: UUID, key: str, path: Path) -> ObjectMetadata: ...
    def read(self, workspace_id: UUID, key: str) -> bytes: ...
    def exists(self, workspace_id: UUID, key: str) -> bool: ...
    def inspect(self, workspace_id: UUID, key: str) -> ObjectMetadata: ...
    def verify(self, workspace_id: UUID, key: str, expected_sha256: str) -> bool: ...
    def delete_staging(self, workspace_id: UUID, prefix: str) -> int: ...
    def list_attempts(self, workspace_id: UUID) -> list[AttemptMetadata]: ...
    def delete_attempt(self, workspace_id: UUID, prefix: str) -> int: ...


def canonical_key(workspace_id: UUID, key: str) -> str:
    normalized = key.strip().replace("\\", "/").lstrip("/")
    prefix = f"workspaces/{workspace_id}/"
    if not normalized.startswith(prefix) or ".." in normalized.split("/"):
        raise ValueError("Storage key is outside the workspace namespace.")
    return normalized


def _attempt_prefix(workspace_id: UUID, prefix: str) -> str:
    key = canonical_key(workspace_id, prefix).rstrip("/")
    parts = key.split("/")
    if len(parts) != 4 or parts[:3] != ["workspaces", str(workspace_id), "a"]:
        raise ValueError("Only an exact generated capture-attempt prefix may be deleted.")
    UUID(parts[3])
    return key


class LocalSnapshotStore:
    """Local development store with strict generated-key validation."""

    def __init__(self, root: str):
        self.root = Path(root).resolve()

    def _path(self, workspace_id: UUID, key: str) -> Path:
        resolved = (self.root / canonical_key(workspace_id, key)).resolve()
        if self.root not in resolved.parents:
            raise ValueError("Storage key escapes the configured root.")
        return resolved

    def put(self, workspace_id: UUID, key: str, body: bytes) -> ObjectMetadata:
        path = self._path(workspace_id, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError("Immutable storage objects cannot be overwritten.")
        temporary = path.with_suffix(path.suffix + ".uploading")
        try:
            with temporary.open("xb") as handle:
                handle.write(body)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return self.inspect(workspace_id, key)

    def put_file(self, workspace_id: UUID, key: str, path: Path) -> ObjectMetadata:
        """Publish an already-streamed file without materialising it in memory."""
        destination = self._path(workspace_id, key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError("Immutable storage objects cannot be overwritten.")
        temporary = destination.with_suffix(destination.suffix + ".uploading")
        try:
            with path.open("rb") as source, temporary.open("xb") as target:
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return self.inspect(workspace_id, key)

    def read(self, workspace_id: UUID, key: str) -> bytes:
        return self._path(workspace_id, key).read_bytes()

    def exists(self, workspace_id: UUID, key: str) -> bool:
        return self._path(workspace_id, key).is_file()

    def inspect(self, workspace_id: UUID, key: str) -> ObjectMetadata:
        path = self._path(workspace_id, key)
        if not path.is_file():
            raise FileNotFoundError("Snapshot object is unavailable.")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return ObjectMetadata(key=canonical_key(workspace_id, key), size_bytes=path.stat().st_size, sha256=digest)

    def verify(self, workspace_id: UUID, key: str, expected_sha256: str) -> bool:
        return self.inspect(workspace_id, key).sha256 == expected_sha256

    def delete_staging(self, workspace_id: UUID, prefix: str) -> int:
        """Delete only generated staging files, never ready snapshot objects."""
        key = canonical_key(workspace_id, prefix)
        if "/.staging-" not in key and not key.endswith(".uploading"):
            raise ValueError("Only staging prefixes are eligible for cleanup.")
        path = self._path(workspace_id, key)
        if not path.exists():
            return 0
        if path.is_file():
            path.unlink()
            return 1
        import shutil
        shutil.rmtree(path)
        return 1

    def list_attempts(self, workspace_id: UUID) -> list[AttemptMetadata]:
        root = self._path(workspace_id, f"workspaces/{workspace_id}/a")
        if not root.is_dir():
            return []
        attempts = []
        for directory in root.iterdir():
            if not directory.is_dir():
                continue
            try:
                prefix = _attempt_prefix(workspace_id, f"workspaces/{workspace_id}/a/{directory.name}")
            except (ValueError, TypeError):
                continue
            attempts.append(AttemptMetadata(prefix, datetime.fromtimestamp(directory.stat().st_mtime, timezone.utc)))
        return sorted(attempts, key=lambda item: item.prefix)

    def delete_attempt(self, workspace_id: UUID, prefix: str) -> int:
        path = self._path(workspace_id, _attempt_prefix(workspace_id, prefix))
        if not path.exists():
            return 0
        import shutil
        shutil.rmtree(path)
        return 1

    def read_manifest(self, workspace_id: UUID, key: str) -> dict:
        return json.loads(self.read(workspace_id, key))

    def publish_manifest(self, workspace_id: UUID, key: str, manifest: dict) -> ObjectMetadata:
        body = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return self.put(workspace_id, key, body)


class S3SnapshotStore:
    """S3/MinIO adapter. Credentials stay server-side in the SDK client."""

    def __init__(self, bucket: str, endpoint_url: str = "", access_key: str = "", secret_key: str = "", region: str = "us-east-1"):
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("S3 snapshot storage requires boto3.") from exc
        self.bucket = bucket
        self.client = boto3.client(
            "s3", endpoint_url=endpoint_url or None, aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None, region_name=region,
        )

    def put(self, workspace_id: UUID, key: str, body: bytes) -> ObjectMetadata:
        key = canonical_key(workspace_id, key)
        if self.exists(workspace_id, key):
            raise FileExistsError("Immutable storage objects cannot be overwritten.")
        digest = hashlib.sha256(body).hexdigest()
        # Callers use unique attempt-scoped keys. The preflight protects normal
        # duplicate calls; authoritative publication additionally remains
        # fenced by the durable metadata transaction.
        self.client.put_object(Bucket=self.bucket, Key=key, Body=body, Metadata={"sha256": digest})
        return ObjectMetadata(key=key, size_bytes=len(body), sha256=digest)

    def put_file(self, workspace_id: UUID, key: str, path: Path) -> ObjectMetadata:
        key = canonical_key(workspace_id, key)
        if self.exists(workspace_id, key):
            raise FileExistsError("Immutable storage objects cannot be overwritten.")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        self.client.upload_file(
            str(path), self.bucket, key, ExtraArgs={"Metadata": {"sha256": digest.hexdigest()}},
        )
        return ObjectMetadata(key=key, size_bytes=path.stat().st_size, sha256=digest.hexdigest())

    def read(self, workspace_id: UUID, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=canonical_key(workspace_id, key))["Body"].read()

    def exists(self, workspace_id: UUID, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=canonical_key(workspace_id, key))
            return True
        except Exception as exc:
            code = getattr(getattr(exc, "response", {}), "get", lambda *_: None)("Error", {}).get("Code")
            if str(code) in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    def inspect(self, workspace_id: UUID, key: str) -> ObjectMetadata:
        key = canonical_key(workspace_id, key)
        response = self.client.head_object(Bucket=self.bucket, Key=key)
        return ObjectMetadata(key=key, size_bytes=int(response["ContentLength"]), sha256=response.get("Metadata", {}).get("sha256", ""))

    def verify(self, workspace_id: UUID, key: str, expected_sha256: str) -> bool:
        return hashlib.sha256(self.read(workspace_id, key)).hexdigest() == expected_sha256

    def delete_staging(self, workspace_id: UUID, prefix: str) -> int:
        prefix = canonical_key(workspace_id, prefix)
        if "/.staging-" not in prefix and not prefix.endswith(".uploading"):
            raise ValueError("Only staging prefixes are eligible for cleanup.")
        response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        keys = [{"Key": item["Key"]} for item in response.get("Contents", [])]
        if keys:
            self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": keys, "Quiet": True})
        return len(keys)

    def list_attempts(self, workspace_id: UUID) -> list[AttemptMetadata]:
        root = canonical_key(workspace_id, f"workspaces/{workspace_id}/a/")
        attempts: dict[str, datetime] = {}
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=root):
            for item in page.get("Contents", []):
                suffix = item["Key"].removeprefix(root).split("/", 1)[0]
                try:
                    prefix = _attempt_prefix(workspace_id, root + suffix)
                except ValueError:
                    continue
                modified = item["LastModified"]
                attempts[prefix] = max(attempts.get(prefix, modified), modified)
        return [AttemptMetadata(prefix, modified) for prefix, modified in sorted(attempts.items())]

    def delete_attempt(self, workspace_id: UUID, prefix: str) -> int:
        prefix = _attempt_prefix(workspace_id, prefix) + "/"
        keys = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            keys.extend({"Key": item["Key"]} for item in page.get("Contents", []))
        for offset in range(0, len(keys), 1000):
            self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": keys[offset:offset + 1000], "Quiet": True})
        return len(keys)

    def read_manifest(self, workspace_id: UUID, key: str) -> dict:
        return json.loads(self.read(workspace_id, key))

    def publish_manifest(self, workspace_id: UUID, key: str, manifest: dict) -> ObjectMetadata:
        return self.put(workspace_id, key, json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def snapshot_store_from_settings(settings) -> SnapshotStore:
    if settings.historical_storage_backend == "local":
        return LocalSnapshotStore(settings.historical_storage_dir)
    return S3SnapshotStore(
        settings.historical_s3_bucket, settings.historical_s3_endpoint_url,
        settings.historical_s3_access_key, settings.historical_s3_secret_key, settings.historical_s3_region,
    )
