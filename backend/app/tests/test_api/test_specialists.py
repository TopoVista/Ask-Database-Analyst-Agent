"""Tests for specialists API."""

from __future__ import annotations

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_list_specialists(client):
    response = await client.get("/api/v1/specialists/")
    assert response.status_code == 200
    data = response.json()
    assert "specialists" in data
    assert isinstance(data["specialists"], list)
    assert data["count"] > 0


@pytest.mark.asyncio
async def test_get_specialist(client):
    response = await client.get("/api/v1/specialists/sql_database_analyst")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "sql_database_analyst"
    assert "capabilities" in data


@pytest.mark.asyncio
async def test_get_nonexistent_specialist(client):
    response = await client.get("/api/v1/specialists/nonexistent")
    assert response.status_code == 404
