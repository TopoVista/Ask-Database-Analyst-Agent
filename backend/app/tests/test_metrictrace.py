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


async def test_replay_options_are_scoped_to_the_workspace(client):
    fixture = (await client.post("/api/v1/metrictrace/demo")).json()
    response = await client.get(f"/api/v1/metrictrace/replay-options?workspace_id={fixture['workspace_id']}")
    assert response.status_code == 200
    body = response.json()
    assert len(body["dataset_versions"]) >= 2
    assert len(body["metric_definitions"]) >= 2
    denied = await client.get("/api/v1/metrictrace/replay-options?workspace_id=00000000-0000-0000-0000-000000000000")
    assert denied.status_code == 404


async def test_replay_workspace_bootstrap_returns_only_the_authenticated_default_workspace(client):
    empty = await client.get("/api/v1/metrictrace/replay-workspace")
    assert empty.status_code == 200, empty.text
    assert empty.json()["workspace_id"]
    assert empty.json()["options"] == {"dataset_versions": [], "metric_definitions": []}

    fixture = (await client.post("/api/v1/metrictrace/demo")).json()
    populated = await client.get("/api/v1/metrictrace/replay-workspace")
    assert populated.status_code == 200
    assert populated.json()["workspace_id"] == fixture["workspace_id"]
    assert len(populated.json()["options"]["dataset_versions"]) == 2


async def test_postgres_discovery_requires_an_owned_postgres_connection(client):
    fixture = (await client.post("/api/v1/metrictrace/demo")).json()
    response = await client.post(
        "/api/v1/metrictrace/sources/postgresql/discover",
        json={
            "workspace_id": fixture["workspace_id"],
            "connection_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert response.status_code == 404
    assert "PostgreSQL connection" in response.json()["detail"]


async def test_metric_sources_are_listed_only_for_the_authenticated_workspace(client):
    fixture = (await client.post("/api/v1/metrictrace/demo")).json()
    response = await client.get(f"/api/v1/metrictrace/sources?workspace_id={fixture['workspace_id']}")
    assert response.status_code == 200
    source = response.json()["sources"][0]
    assert source["name"] == "Monday revenue fixture"
    assert source["version_count"] == 2

    denied = await client.get("/api/v1/metrictrace/sources?workspace_id=00000000-0000-0000-0000-000000000000")
    assert denied.status_code == 404


async def test_dataset_diff_uses_owned_immutable_versions_without_accepting_paths(client):
    fixture = (await client.post("/api/v1/metrictrace/demo")).json()
    response = await client.post(
        "/api/v1/metrictrace/dataset-diff",
        json={
            "workspace_id": fixture["workspace_id"],
            "old_version_id": fixture["inputs"]["old_dataset_version"],
            "new_version_id": fixture["inputs"]["new_dataset_version"],
            "key_columns": ["order_id"],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["old_version_id"] == fixture["inputs"]["old_dataset_version"]
    assert body["comparison"]["summary"] == {
        "mode": "stable_key", "comparable": True, "inserted": 0, "deleted": 0, "modified": 2, "unchanged": 0,
    }
    assert {record["key"]["order_id"] for record in body["comparison"]["records"]} == {"a-1", "a-2"}


async def test_sql_regression_runs_shared_engine_against_an_owned_immutable_version(client):
    fixture = (await client.post("/api/v1/metrictrace/demo")).json()
    response = await client.post(
        "/api/v1/metrictrace/sql-regression",
        json={
            "workspace_id": fixture["workspace_id"],
            "dataset_version_id": fixture["inputs"]["old_dataset_version"],
            "baseline_sql": "SELECT SUM(amount_inr) FROM source_data WHERE status = 'paid'",
            "candidate_sql": "SELECT SUM(amount_inr) FROM source_data WHERE status = 'paid' AND channel <> 'marketplace'",
            "max_absolute_difference": "250000",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()["regression"]
    assert body["baseline"]["value"] == "2400000"
    assert body["candidate"]["value"] == "2100000"
    assert body["gates"] == [{"type": "absolute_difference", "limit": "250000", "actual": "300000", "status": "FAIL"}]


async def test_join_audit_uses_only_the_owned_snapshot_manifest_tables(client):
    fixture = (await client.post("/api/v1/metrictrace/demo")).json()
    response = await client.post(
        "/api/v1/metrictrace/join-audit",
        json={
            "workspace_id": fixture["workspace_id"],
            "dataset_version_id": fixture["inputs"]["old_dataset_version"],
            "sql": "SELECT * FROM source_data",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tables"] == [{"schema": "", "table": "source_data", "sql_name": "source_data"}]
    assert body["audit"]["supported"] is False
