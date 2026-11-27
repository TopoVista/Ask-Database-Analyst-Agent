"""Immutable local object-store implementation for development and tests."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any


class LocalParquetStorage:
    """Writes a complete staging version before atomically publishing it."""

    def __init__(self, root: str):
        self.root = Path(root).resolve()

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _version_dir(self, workspace_id: uuid.UUID, source_id: uuid.UUID, version_id: uuid.UUID) -> Path:
        return self.root / "workspaces" / str(workspace_id) / "sources" / str(source_id) / "versions" / str(version_id)

    def publish_records(
        self, workspace_id: uuid.UUID, source_id: uuid.UUID, records: list[dict[str, Any]]
    ) -> tuple[uuid.UUID, str, str, int, dict[str, Any]]:
        if not records:
            raise ValueError("A snapshot must include at least one record.")
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as exc:  # pragma: no cover - surfaced at deployment configuration
            raise RuntimeError("Historical capture requires pyarrow. Install backend requirements.") from exc

        version_id = uuid.uuid4()
        final_dir = self._version_dir(workspace_id, source_id, version_id)
        staging_dir = final_dir.with_name(f".staging-{version_id}")
        staging_dir.mkdir(parents=True, exist_ok=False)
        try:
            table = pa.Table.from_pylist(records)
            parquet_path = staging_dir / "data.parquet"
            pq.write_table(table, parquet_path, compression="zstd")
            schema = {field.name: str(field.type) for field in table.schema}
            (staging_dir / "schema.json").write_text(json.dumps(schema, sort_keys=True), encoding="utf-8")
            manifest = {
                "format_version": 1,
                "row_count": table.num_rows,
                "schema": schema,
                "objects": [{"key": "data.parquet", "sha256": self._sha256(parquet_path), "bytes": parquet_path.stat().st_size}],
            }
            manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
            (staging_dir / "manifest.json").write_bytes(manifest_bytes)
            content_hash = hashlib.sha256(manifest_bytes).hexdigest()
            byte_size = parquet_path.stat().st_size
            os.replace(staging_dir, final_dir)
            relative_manifest = final_dir.relative_to(self.root).joinpath("manifest.json").as_posix()
            return version_id, relative_manifest, content_hash, byte_size, schema
        except Exception:
            if staging_dir.exists():
                shutil.rmtree(staging_dir)
            raise

    def parquet_path(self, manifest_uri: str) -> Path:
        manifest_path = (self.root / manifest_uri).resolve()
        if self.root not in manifest_path.parents or manifest_path.name != "manifest.json":
            raise ValueError("Invalid metric storage manifest reference.")
        if not manifest_path.is_file():
            raise FileNotFoundError("Historical snapshot object is unavailable.")
        return manifest_path.parent / "data.parquet"
