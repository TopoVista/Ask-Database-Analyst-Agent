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
