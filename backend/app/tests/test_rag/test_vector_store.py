"""Tests for vector store implementations."""

from __future__ import annotations

import pytest

from app.rag.vector_store import (
    InMemoryVectorStore,
    StoredChunk,
    VectorStore,
    get_default_store,
    get_vector_store,
)


def _make_chunk(chunk_id: str, text: str, user_id: str = "user-1", embedding: list[float] | None = None) -> StoredChunk:
    if embedding is None:
        # Simple deterministic embedding based on text length
        embedding = [float(len(text)), 1.0, 0.0]
    return StoredChunk(
        id=chunk_id,
        text=text,
        source="test.txt",
        chunk_index=0,
        embedding=embedding,
        user_id=user_id,
    )


class TestInMemoryVectorStore:
    @pytest.mark.asyncio
    async def test_add_and_count(self):
        store = InMemoryVectorStore()
        assert store.count() == 0
        await store.add_chunks([_make_chunk("1", "hello")])
        assert store.count() == 1

    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        store = InMemoryVectorStore()
        chunk = _make_chunk("1", "hello world", embedding=[1.0, 0.0, 0.0])
        await store.add_chunks([chunk])
        results = await store.search([1.0, 0.0, 0.0], limit=5)
        assert len(results) == 1
        assert results[0][0].text == "hello world"
        assert results[0][1] > 0.9  # High similarity

    @pytest.mark.asyncio
    async def test_search_scoped_by_user(self):
        store = InMemoryVectorStore()
        chunk1 = _make_chunk("1", "user1 doc", user_id="user-1", embedding=[1.0, 0.0])
        chunk2 = _make_chunk("2", "user2 doc", user_id="user-2", embedding=[1.0, 0.0])
        await store.add_chunks([chunk1, chunk2])

        results = await store.search([1.0, 0.0], user_id="user-1")
        assert len(results) == 1
        assert results[0][0].user_id == "user-1"

    @pytest.mark.asyncio
    async def test_search_scoped_by_source(self):
        store = InMemoryVectorStore()
        chunk1 = _make_chunk("1", "doc from A", user_id="user-1")
        chunk1.source = "source_a.txt"
        chunk2 = _make_chunk("2", "doc from B", user_id="user-1")
        chunk2.source = "source_b.txt"
        await store.add_chunks([chunk1, chunk2])

        results = await store.search([1.0, 0.0], user_id="user-1", source="source_a.txt")
        assert len(results) == 1
        assert results[0][0].source == "source_a.txt"

    @pytest.mark.asyncio
    async def test_delete_by_user(self):
        store = InMemoryVectorStore()
        chunk1 = _make_chunk("1", "user1 doc", user_id="user-1")
        chunk2 = _make_chunk("2", "user2 doc", user_id="user-2")
        await store.add_chunks([chunk1, chunk2])

        deleted = await store.delete_by_user("user-1")
        assert deleted == 1
        assert store.count() == 1

    @pytest.mark.asyncio
    async def test_delete_by_source(self):
        store = InMemoryVectorStore()
        chunk1 = _make_chunk("1", "doc A", user_id="user-1")
        chunk1.source = "a.txt"
        chunk2 = _make_chunk("2", "doc B", user_id="user-1")
        chunk2.source = "b.txt"
        await store.add_chunks([chunk1, chunk2])

        deleted = await store.delete_by_source("a.txt")
        assert deleted == 1
        assert store.count() == 1

    @pytest.mark.asyncio
    async def test_search_empty_store(self):
        store = InMemoryVectorStore()
        results = await store.search([1.0, 0.0])
        assert results == []


class TestFactory:
    def test_get_vector_store_returns_store(self):
        store = get_vector_store()
        assert isinstance(store, VectorStore)

    def test_get_default_store_returns_singleton(self):
        store1 = get_default_store()
        store2 = get_default_store()
        assert store1 is store2
