"""Tests for document upload and RAG retrieval API."""

from __future__ import annotations

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_upload_document(client):
    content = b"The capital of France is Paris. The capital of Germany is Berlin."
    response = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", content, "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["num_chunks"] >= 1


@pytest.mark.asyncio
async def test_upload_unsupported_type(client):
    response = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.xyz", b"data", "application/octet-stream")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_search_documents(client):
    content = b"The capital of France is Paris. The capital of Germany is Berlin."
    await client.post(
        "/api/v1/documents/upload",
        files={"file": ("capitals.txt", content, "text/plain")},
    )

    response = await client.post(
        "/api/v1/documents/search",
        params={"query": "capital of France", "limit": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)
