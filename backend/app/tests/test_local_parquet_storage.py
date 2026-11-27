from __future__ import annotations

import pytest

from app.infrastructure.storage import local_parquet
from app.infrastructure.storage.local_parquet import LocalParquetStorage


def test_local_parquet_publish_retries_only_transient_permission_error(tmp_path, monkeypatch):
    staging_dir, final_dir = tmp_path / "staging", tmp_path / "final"
    staging_dir.mkdir()
    original_replace = local_parquet.os.replace
    attempts = 0

    def transient_replace(source, target):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError("simulated transient Windows handle contention")
        return original_replace(source, target)

    monkeypatch.setattr(local_parquet.os, "replace", transient_replace)
    monkeypatch.setattr(local_parquet.time, "sleep", lambda _: None)

    LocalParquetStorage._publish_directory(staging_dir, final_dir)

    assert attempts == 2
    assert final_dir.is_dir()


def test_local_parquet_publish_does_not_mask_persistent_permission_error(tmp_path, monkeypatch):
    staging_dir, final_dir = tmp_path / "staging", tmp_path / "final"
    staging_dir.mkdir()
    monkeypatch.setattr(local_parquet.os, "replace", lambda *_: (_ for _ in ()).throw(PermissionError("busy")))
    monkeypatch.setattr(local_parquet.time, "sleep", lambda _: None)

    with pytest.raises(PermissionError, match="busy"):
        LocalParquetStorage._publish_directory(staging_dir, final_dir)
