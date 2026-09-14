"""Tests for the isolated specialist and RAG worker contracts."""

from __future__ import annotations

import base64

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.rag import vector_store
from app.rag.vector_store import DatabaseVectorStore, StoredChunk
from app.services.worker_client import specialist_worker_url
from app.workers.rag_service import app as rag_app
from app.workers.specialist_service import app as specialist_app


@pytest.mark.asyncio
async def test_specialist_worker_requires_token_and_executes_assigned_skill(monkeypatch):
    monkeypatch.setenv("WORKER_SHARED_TOKEN", "test-token")
    monkeypatch.setenv("WORKER_SPECIALISTS", "nlp_text_analyst")
    get_settings.cache_clear()
    async with AsyncClient(transport=ASGITransport(app=specialist_app), base_url="http://worker") as client:
        denied = await client.post(
            "/v1/specialists/nlp_text_analyst/invoke",
            json={"skill": "sentiment", "params": {"text": "great"}},
        )
        assert denied.status_code == 401

        allowed = await client.post(
            "/v1/specialists/nlp_text_analyst/invoke",
            headers={"X-Worker-Token": "test-token"},
            json={"skill": "sentiment", "params": {"text": "great product"}},
        )
    get_settings.cache_clear()
    assert allowed.status_code == 200
    assert allowed.json()["result"]["label"] == "positive"


@pytest.mark.asyncio
async def test_rag_worker_ingests_and_searches_with_token(monkeypatch):
    monkeypatch.setenv("WORKER_SHARED_TOKEN", "test-token")
    monkeypatch.setenv("RAG_STORE_BACKEND", "in_memory")
    get_settings.cache_clear()
    vector_store._default_store = None
    content = b"The capital of France is Paris. Berlin is in Germany."
    async with AsyncClient(transport=ASGITransport(app=rag_app), base_url="http://worker") as client:
        ingest = await client.post(
            "/v1/documents/ingest",
            headers={"X-Worker-Token": "test-token"},
            json={
                "content_base64": base64.b64encode(content).decode("ascii"),
                "source": "capitals.txt",
                "user_id": "user-1",
            },
        )
        assert ingest.status_code == 200
        search = await client.post(
            "/v1/documents/search",
            headers={"X-Worker-Token": "test-token"},
            json={"query": "capital France", "user_id": "user-1", "limit": 3},
        )
    vector_store._default_store = None
    get_settings.cache_clear()
    assert search.status_code == 200
    assert search.json()["count"] >= 1


@pytest.mark.asyncio
async def test_database_vector_store_is_durable_and_user_scoped(tmp_path):
    store = DatabaseVectorStore(f"sqlite+aiosqlite:///{tmp_path / 'rag.db'}", candidate_limit=50)
    try:
        await store.add_chunks(
            [
                StoredChunk("a", "Paris information", "a.txt", 0, [1.0, 0.0], user_id="user-1"),
                StoredChunk("b", "other user", "b.txt", 0, [1.0, 0.0], user_id="user-2"),
            ]
        )
        results = await store.search([1.0, 0.0], user_id="user-1")
        assert len(results) == 1
        assert results[0][0].source == "a.txt"
        assert await store.delete_by_source("a.txt", user_id="user-1") == 1
    finally:
        await store.aclose()


def test_specialist_worker_url_mapping(monkeypatch):
    monkeypatch.setenv("SPECIALIST_WORKER_URLS", "ml_scientist=http://ml:10000, anomaly_advanced=http://anomaly:10000")
    get_settings.cache_clear()
    assert specialist_worker_url("anomaly_advanced") == "http://anomaly:10000"
    assert specialist_worker_url("dashboard_expert") == ""
    get_settings.cache_clear()
