"""Tests for dataset ingestion, profiling, and the datasets API."""

from __future__ import annotations

import io

import pytest


CSV_CONTENT = (
    b"order_id,customer_name,order_date,amount,region\n"
    b"1,Alice,2026-01-05,120.5,west\n"
    b"2,Bob,2026-01-06,80.0,east\n"
    b"3,carol@ex.com,2026-01-07,,west\n"
    b"4,Dan,2026-02-01,220.25,east\n"
    b"5,Eve,2026-02-03,95.0,west\n"
)


def _csv_file(name="sales.csv"):
    return {"file": (name, io.BytesIO(CSV_CONTENT), "text/csv")}


@pytest.mark.asyncio
async def test_upload_and_list_datasets(client):
    resp = await client.post("/api/v1/datasets", files=_csv_file())
    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "sales.csv"
    assert data["row_count"] == 5
    assert data["column_count"] == 5
    descriptor = data["descriptor"]
    assert descriptor["table_name"] == "sales"
    # Semantic typing
    semantics = {c["name"]: c["semantic_type"] for c in descriptor["columns"]}
    assert semantics["amount"] == "measure"
    assert semantics["order_date"] == "temporal"
    assert semantics["region"] == "categorical"

    listing = (await client.get("/api/v1/datasets")).json()
    assert listing["total"] == 1
    assert listing["datasets"][0]["id"] == data["id"]


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_type(client):
    resp = await client.post(
        "/api/v1/datasets",
        files={"file": ("evil.exe", io.BytesIO(b"MZ..."), "application/octet-stream")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_empty_csv(client):
    resp = await client.post(
        "/api/v1/datasets",
        files={"file": ("empty.csv", io.BytesIO(b"a,b\n"), "text/csv")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_dataset_ownership(client):
    created = (await client.post("/api/v1/datasets", files=_csv_file())).json()
    ok = await client.get(f"/api/v1/datasets/{created['id']}")
    assert ok.status_code == 200
    missing = await client.get("/api/v1/datasets/nonexistent")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_preview_dataset(client):
    created = (await client.post("/api/v1/datasets", files=_csv_file())).json()
    resp = await client.get(f"/api/v1/datasets/{created['id']}/preview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["table_name"] == "sales"
    assert body["columns"] == ["order_id", "customer_name", "order_date", "amount", "region"]
    assert len(body["rows_preview"]) == 5


@pytest.mark.asyncio
async def test_deep_profile_endpoint(client):
    created = (await client.post("/api/v1/datasets", files=_csv_file())).json()
    resp = await client.post(f"/api/v1/datasets/{created['id']}/profile")
    assert resp.status_code == 200
    descriptor = resp.json()["descriptor"]
    assert descriptor["deep_profiled"] is True
    # Quality report detects the missing amount value
    assert descriptor["quality_report"].get("total_missing", 0) >= 1


@pytest.mark.asyncio
async def test_delete_dataset(client):
    created = (await client.post("/api/v1/datasets", files=_csv_file())).json()
    resp = await client.delete(f"/api/v1/datasets/{created['id']}")
    assert resp.status_code == 204
    listing = (await client.get("/api/v1/datasets")).json()
    assert listing["total"] == 0
