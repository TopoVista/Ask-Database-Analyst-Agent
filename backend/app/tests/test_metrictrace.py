from __future__ import annotations

import pytest


async def test_static_lineage_api_uses_authenticated_workspace_scope(client):
    fixture = (await client.post("/api/v1/metrictrace/demo")).json()
    response = await client.post(
        "/api/v1/metrictrace/lineage/inspect",
        json={
            "workspace_id": fixture["workspace_id"],
            "sql": "SELECT SUM(amount_inr) AS revenue FROM source_data",
            "tables": ["source_data"],
        },
    )

    assert response.status_code == 200
    assert response.json()["lineage"]["source_tables"] == ["source_data"]
    denied = await client.post(
        "/api/v1/metrictrace/lineage/inspect",
        json={
            "workspace_id": "00000000-0000-0000-0000-000000000000",
            "sql": "SELECT SUM(amount_inr) FROM source_data",
            "tables": ["source_data"],
        },
    )
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_canonical_metrictrace_replay_is_deterministic_and_reconciles(client):
    first = await client.post("/api/v1/metrictrace/demo")
    assert first.status_code == 200, first.text
    body = first.json()

    assert body["status"] == "completed"
    assert body["attribution"]["reconciles"] is True
    assert body["attribution"]["data_effect"] == "-180000"
    assert body["attribution"]["definition_effect"] == "-300000"
    assert body["attribution"]["interaction_effect"] == "-120000"
    assert body["attribution"]["data_contribution"] == "-240000"
    assert body["attribution"]["definition_contribution"] == "-360000"
    assert len(body["cells"]) == 4
    results = {cell["label"]: cell["result_inr"] for cell in body["cells"]}
    assert results["old_data_old_definition"] == "2400000"
    assert results == {
        "old_data_old_definition": "2400000",
        "old_data_new_definition": "2100000",
        "new_data_old_definition": "2220000",
        "new_data_new_definition": "1800000",
    }
    assert all(cell["status"] == "completed" for cell in body["cells"])

    second = await client.post("/api/v1/metrictrace/demo")
    assert second.status_code == 200, second.text
    assert second.json()["attribution"] == body["attribution"]
