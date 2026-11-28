from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import boto3
import pytest

from app.infrastructure.storage.snapshot_store import S3SnapshotStore


class _S3NotFound(Exception):
    def __init__(self):
        self.response = {"Error": {"Code": "404"}}


class _Paginator:
    def __init__(self, client: "_FakeS3"):
        self.client = client

    def paginate(self, *, Bucket: str, Prefix: str):
        yield self.client.list_objects_v2(Bucket=Bucket, Prefix=Prefix)


class _FakeS3:
    def __init__(self):
        self.objects: dict[tuple[str, str], tuple[bytes, dict[str, str], datetime]] = {}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, Metadata: dict[str, str]):
        self.objects[(Bucket, Key)] = (Body, Metadata, datetime.now(timezone.utc))

    def upload_file(self, filename: str, bucket: str, key: str, ExtraArgs: dict):
        self.put_object(
            Bucket=bucket,
            Key=key,
            Body=Path(filename).read_bytes(),
            Metadata=ExtraArgs["Metadata"],
        )

    def get_object(self, *, Bucket: str, Key: str):
        body, _, _ = self._object(Bucket, Key)
        return {"Body": BytesIO(body)}

    def head_object(self, *, Bucket: str, Key: str):
        body, metadata, _ = self._object(Bucket, Key)
        return {"ContentLength": len(body), "Metadata": metadata}

    def list_objects_v2(self, *, Bucket: str, Prefix: str):
        contents = [
            {"Key": key, "LastModified": modified}
            for (bucket, key), (_, _, modified) in sorted(self.objects.items())
            if bucket == Bucket and key.startswith(Prefix)
        ]
        return {"Contents": contents}

    def get_paginator(self, operation: str):
        assert operation == "list_objects_v2"
        return _Paginator(self)

    def delete_objects(self, *, Bucket: str, Delete: dict):
        for entry in Delete["Objects"]:
            self.objects.pop((Bucket, entry["Key"]), None)

    def _object(self, bucket: str, key: str):
        try:
            return self.objects[(bucket, key)]
        except KeyError as exc:
            raise _S3NotFound from exc


def test_s3_store_matches_immutable_workspace_scoped_snapshot_contract(tmp_path, monkeypatch):
    fake = _FakeS3()
    monkeypatch.setattr(boto3, "client", lambda *_args, **_kwargs: fake)
    store = S3SnapshotStore("metrictrace", endpoint_url="http://minio.test")
    workspace, other = uuid4(), uuid4()
    key = f"workspaces/{workspace}/a/{uuid4()}/manifest.json"

    metadata = store.put(workspace, key, b'{"complete":true}')
    assert metadata.size_bytes == len(b'{"complete":true}')
    assert store.verify(workspace, key, metadata.sha256)
    assert store.read_manifest(workspace, key) == {"complete": True}
    with pytest.raises(FileExistsError):
        store.put(workspace, key, b"replacement")
    with pytest.raises(ValueError):
        store.read(other, key)

    source = tmp_path / "orders.parquet"
    source.write_bytes(b"parquet-bytes")
    table_key = f"workspaces/{workspace}/a/{uuid4()}/tables/0.parquet"
    uploaded = store.put_file(workspace, table_key, source)
    assert uploaded.size_bytes == len(b"parquet-bytes")
    assert store.verify(workspace, table_key, uploaded.sha256)
    with pytest.raises(FileExistsError):
        store.put_file(workspace, table_key, source)


def test_s3_store_lists_and_cleans_only_generated_attempt_prefixes(monkeypatch):
    fake = _FakeS3()
    monkeypatch.setattr(boto3, "client", lambda *_args, **_kwargs: fake)
    store = S3SnapshotStore("metrictrace", endpoint_url="http://minio.test")
    workspace, first, second = uuid4(), uuid4(), uuid4()
    first_prefix = f"workspaces/{workspace}/a/{first}"
    second_prefix = f"workspaces/{workspace}/a/{second}"
    store.put(workspace, f"{first_prefix}/manifest.json", b"{}")
    store.put(workspace, f"{first_prefix}/tables/0.parquet", b"one")
    store.put(workspace, f"{second_prefix}/manifest.json", b"{}")

    assert [attempt.prefix for attempt in store.list_attempts(workspace)] == [first_prefix, second_prefix]
    assert store.delete_attempt(workspace, first_prefix) == 2
    assert [attempt.prefix for attempt in store.list_attempts(workspace)] == [second_prefix]
    with pytest.raises(ValueError):
        store.delete_attempt(workspace, f"workspaces/{workspace}/a/not-a-uuid")
