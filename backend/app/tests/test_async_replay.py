from __future__ import annotations

import pytest

from app.workers.metrictrace import MetricTraceWorker


@pytest.mark.asyncio
async def test_replay_is_persisted_then_completed_by_independent_cell_jobs(client):
    fixture = (await client.post("/api/v1/metrictrace/demo")).json()
    payload = {
        "workspace_id": fixture["workspace_id"],
        "old_version_id": fixture["inputs"]["old_dataset_version"],
        "new_version_id": fixture["inputs"]["new_dataset_version"],
        "old_definition_id": fixture["inputs"]["old_definition"],
        "new_definition_id": fixture["inputs"]["new_definition"],
    }
    submitted = await client.post("/api/v1/metrictrace/replays", json=payload)
    assert submitted.status_code == 202, submitted.text
    replay_id = submitted.json()["replay_id"]
    queued = await client.get(f"/api/v1/metrictrace/replays/{replay_id}")
    assert queued.json()["status"] == "queued"
    assert {cell["status"] for cell in queued.json()["cells"]} == {"queued"}

    worker = MetricTraceWorker("test-worker")
    for _ in range(4):
        assert await worker.run_once()
    finished = await client.get(f"/api/v1/metrictrace/replays/{replay_id}")
    body = finished.json()
    assert body["status"] == "completed"
    assert all(cell["status"] == "completed" for cell in body["cells"])
    assert body["attribution"]["total_change"] == "-600000"


@pytest.mark.asyncio
async def test_authorized_replay_cancellation_fences_all_unpublished_cells(client):
    fixture = (await client.post("/api/v1/metrictrace/demo")).json()
    submitted = await client.post(
        "/api/v1/metrictrace/replays",
        json={
            "workspace_id": fixture["workspace_id"],
            "old_version_id": fixture["inputs"]["old_dataset_version"],
            "new_version_id": fixture["inputs"]["new_dataset_version"],
            "old_definition_id": fixture["inputs"]["old_definition"],
            "new_definition_id": fixture["inputs"]["new_definition"],
        },
    )
    replay_id = submitted.json()["replay_id"]

    cancelled = await client.delete(f"/api/v1/metrictrace/replays/{replay_id}")
    assert cancelled.status_code == 202, cancelled.text
    assert cancelled.json()["status"] == "cancelled"

    replay = await client.get(f"/api/v1/metrictrace/replays/{replay_id}")
    assert replay.json()["status"] == "cancelled"
    assert {cell["status"] for cell in replay.json()["cells"]} == {"cancelled"}

    assert not await MetricTraceWorker("cancelled-worker").run_once()
