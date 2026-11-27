from __future__ import annotations

from uuid import uuid4
from datetime import datetime, timezone

import pytest

from app.infrastructure.storage.snapshot_store import LocalSnapshotStore, canonical_key


def test_local_snapshot_store_is_workspace_scoped_and_immutable(tmp_path):
    workspace = uuid4()
    store = LocalSnapshotStore(str(tmp_path))
    key = f"workspaces/{workspace}/sources/source/versions/version/manifest.json"
    metadata = store.put(workspace, key, b'{"complete":true}')

    assert metadata.size_bytes == len(b'{"complete":true}')
    assert store.exists(workspace, key)
    assert store.verify(workspace, key, metadata.sha256)
    assert store.read_manifest(workspace, key) == {"complete": True}
    with pytest.raises(FileExistsError):
        store.put(workspace, key, b"replacement")
    with pytest.raises(ValueError):
        canonical_key(workspace, "workspaces/other/../../secret")


def test_local_store_only_cleans_staging(tmp_path):
    workspace = uuid4()
    store = LocalSnapshotStore(str(tmp_path))
    staging = f"workspaces/{workspace}/sources/source/versions/.staging-1/partial.parquet"
    store.put(workspace, staging, b"partial")
    assert store.delete_staging(workspace, f"workspaces/{workspace}/sources/source/versions/.staging-1") == 1
    with pytest.raises(ValueError):
        store.delete_staging(workspace, f"workspaces/{workspace}/sources/source/versions/ready")


def test_local_store_lists_and_deletes_only_exact_generated_attempts(tmp_path):
    workspace, attempt = uuid4(), uuid4()
    store = LocalSnapshotStore(str(tmp_path))
    prefix = f"workspaces/{workspace}/a/{attempt}"
    store.put(workspace, f"{prefix}/manifest.json", b"{}")

    attempts = store.list_attempts(workspace)
    assert [item.prefix for item in attempts] == [prefix]
    assert attempts[0].modified_at <= datetime.now(timezone.utc)
    assert store.delete_attempt(workspace, prefix) == 1
    assert store.list_attempts(workspace) == []
    with pytest.raises(ValueError):
        store.delete_attempt(workspace, f"workspaces/{workspace}/a/not-a-uuid")
