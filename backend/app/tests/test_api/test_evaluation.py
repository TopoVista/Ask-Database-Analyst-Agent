"""Tests for evaluation API."""

from __future__ import annotations

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_security_audit(client):
    response = await client.get("/api/v1/evaluation/security-audit")
    assert response.status_code == 200
    data = response.json()
    assert "passed" in data
    assert "findings" in data
    assert isinstance(data["findings"], list)


@pytest.mark.asyncio
async def test_list_benchmarks(client):
    response = await client.get("/api/v1/evaluation/benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert "benchmarks" in data
    assert isinstance(data["benchmarks"], list)
    assert len(data["benchmarks"]) > 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint, benchmark_id",
    [
        ("/api/v1/evaluation/benchmarks/nlq_to_sql/run", "nlq_to_sql"),
        ("/api/v1/evaluation/benchmarks/nlq/run", "nlq_to_sql"),
        ("/api/v1/evaluation/benchmarks/eda_correctness/run", "eda_correctness"),
        ("/api/v1/evaluation/benchmarks/eda/run", "eda_correctness"),
        ("/api/v1/evaluation/benchmarks/nlp_sentiment/run", "nlp_sentiment"),
        ("/api/v1/evaluation/benchmarks/nlp/run", "nlp_sentiment"),
    ],
)
async def test_benchmarks_are_available_on_canonical_and_legacy_urls(client, endpoint, benchmark_id):
    response = await client.post(endpoint)
    assert response.status_code == 200
    data = response.json()
    assert data["benchmark_id"] == benchmark_id
    assert data["total_cases"] > 0
