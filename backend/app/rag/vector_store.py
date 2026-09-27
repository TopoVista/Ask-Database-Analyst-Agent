"""Lightweight vector stores for document retrieval."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


@dataclass
class StoredChunk:
    id: str
    text: str
    source: str
    chunk_index: int
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    user_id: str | None = None


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    size = min(len(left), len(right))
    if not size:
        return 0.0
    dot = sum(left[index] * right[index] for index in range(size))
    left_norm = math.sqrt(sum(value * value for value in left[:size]))
    right_norm = math.sqrt(sum(value * value for value in right[:size]))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


class VectorStore:
    async def add_chunks(self, chunks: list[StoredChunk]) -> None:
        raise NotImplementedError

    async def search(self, query_embedding: list[float], *, limit: int = 5, user_id: str | None = None, source: str | None = None) -> list[tuple[StoredChunk, float]]:
        raise NotImplementedError

    async def delete_by_user(self, user_id: str) -> int:
        raise NotImplementedError

    async def delete_by_source(self, source: str, *, user_id: str | None = None) -> int:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    """Bounded local-development store; production uses DatabaseVectorStore."""

    def __init__(self) -> None:
        self._items: dict[str, StoredChunk] = {}

    async def add_chunks(self, chunks: list[StoredChunk]) -> None:
        self._items.update({chunk.id: chunk for chunk in chunks})

    async def search(self, query_embedding: list[float], *, limit: int = 5, user_id: str | None = None, source: str | None = None) -> list[tuple[StoredChunk, float]]:
        matches = [
            (chunk, round(_cosine_similarity(query_embedding, chunk.embedding), 4))
            for chunk in self._items.values()
            if (user_id is None or chunk.user_id == user_id) and (source is None or chunk.source == source)
        ]
        return sorted((match for match in matches if match[1] > 0), key=lambda match: match[1], reverse=True)[:limit]

    async def delete_by_user(self, user_id: str) -> int:
        return await self._delete(lambda chunk: chunk.user_id == user_id)

    async def delete_by_source(self, source: str, *, user_id: str | None = None) -> int:
        return await self._delete(lambda chunk: chunk.source == source and (user_id is None or chunk.user_id == user_id))

    async def _delete(self, predicate: Callable[[StoredChunk], bool]) -> int:
        ids = [chunk_id for chunk_id, chunk in self._items.items() if predicate(chunk)]
        for chunk_id in ids:
            del self._items[chunk_id]
        return len(ids)

    def count(self) -> int:
        return len(self._items)


class DatabaseVectorStore(VectorStore):
    """Durable RAG store using the existing managed database and bounded ranking."""

    def __init__(self, database_url: str, candidate_limit: int = 500) -> None:
        self.candidate_limit = candidate_limit
        self._engine = create_async_engine(database_url, future=True, poolclass=NullPool)
        self._initialized = False

    async def _ensure_table(self) -> None:
        if self._initialized:
            return
        async with self._engine.begin() as connection:
            await connection.execute(text(
                "CREATE TABLE IF NOT EXISTS rag_document_chunks ("
                "id VARCHAR(64) PRIMARY KEY, user_id VARCHAR(128) NOT NULL, source VARCHAR(512) NOT NULL, "
                "chunk_index INTEGER NOT NULL, chunk_text TEXT NOT NULL, embedding_json TEXT NOT NULL, "
                "metadata_json TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            ))
            await connection.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_user_source "
                "ON rag_document_chunks (user_id, source)"
            ))
        self._initialized = True

    async def add_chunks(self, chunks: list[StoredChunk]) -> None:
        if not chunks:
            return
        await self._ensure_table()
        rows = [{
            "id": chunk.id, "user_id": chunk.user_id or "", "source": chunk.source,
            "chunk_index": chunk.chunk_index, "chunk_text": chunk.text,
            "embedding_json": json.dumps(chunk.embedding, separators=(",", ":")),
            "metadata_json": json.dumps(chunk.metadata, separators=(",", ":")),
        } for chunk in chunks]
        statement = text(
            "INSERT INTO rag_document_chunks (id, user_id, source, chunk_index, chunk_text, embedding_json, metadata_json) "
            "VALUES (:id, :user_id, :source, :chunk_index, :chunk_text, :embedding_json, :metadata_json)"
        )
        async with self._engine.begin() as connection:
            await connection.execute(statement, rows)

    async def search(self, query_embedding: list[float], *, limit: int = 5, user_id: str | None = None, source: str | None = None) -> list[tuple[StoredChunk, float]]:
        if user_id is None:
            return []
        await self._ensure_table()
        sql = (
            "SELECT id, user_id, source, chunk_index, chunk_text, embedding_json, metadata_json "
            "FROM rag_document_chunks WHERE user_id = :user_id"
        )
        params: dict[str, Any] = {"user_id": user_id, "candidate_limit": self.candidate_limit}
        if source is not None:
            sql += " AND source = :source"
            params["source"] = source
        sql += " ORDER BY created_at DESC LIMIT :candidate_limit"
        async with self._engine.connect() as connection:
            result = await connection.execute(text(sql), params)
            rows = result.mappings().all()
        matches = [
            (StoredChunk(id=row["id"], text=row["chunk_text"], source=row["source"], chunk_index=row["chunk_index"], embedding=[], metadata=json.loads(row["metadata_json"]), user_id=row["user_id"]), round(_cosine_similarity(query_embedding, json.loads(row["embedding_json"])), 4))
            for row in rows
        ]
        return sorted((match for match in matches if match[1] > 0), key=lambda match: match[1], reverse=True)[:limit]

    async def delete_by_user(self, user_id: str) -> int:
        return await self._delete("user_id = :user_id", {"user_id": user_id})

    async def delete_by_source(self, source: str, *, user_id: str | None = None) -> int:
        params: dict[str, Any] = {"source": source}
        condition = "source = :source"
        if user_id is not None:
            condition += " AND user_id = :user_id"
            params["user_id"] = user_id
        return await self._delete(condition, params)

    async def _delete(self, condition: str, params: dict[str, Any]) -> int:
        await self._ensure_table()
        async with self._engine.begin() as connection:
            result = await connection.execute(text(f"DELETE FROM rag_document_chunks WHERE {condition}"), params)
        return int(result.rowcount or 0)

    def count(self) -> int:
        return 0

    async def aclose(self) -> None:
        await self._engine.dispose()


def get_vector_store() -> VectorStore:
    from app.config import get_settings

    settings = get_settings()
    if settings.rag_store_backend.lower() == "database":
        return DatabaseVectorStore(settings.database_url, settings.rag_search_candidate_limit)
    return InMemoryVectorStore()


_default_store: VectorStore | None = None


def get_default_store() -> VectorStore:
    global _default_store
    if _default_store is None:
        _default_store = get_vector_store()
    return _default_store
