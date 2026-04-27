from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy import select

from app.memory.embedding_service import EmbeddingService
from app.models.database import get_sessionmaker
from app.models.query_embedding import QueryEmbedding


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(length))
    norm_a = math.sqrt(sum(v * v for v in a[:length]))
    norm_b = math.sqrt(sum(v * v for v in b[:length]))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


class VectorMemory:
    def __init__(self, user_id: str | uuid.UUID) -> None:
        self.user_id = uuid.UUID(str(user_id))
        self.embedder = EmbeddingService()

    async def store(self, query_text: str, insight_text: str, connection_id: str | uuid.UUID | None = None) -> None:
        if connection_id is None:
            return
        sessionmaker = get_sessionmaker()
        embedding = await self.embedder.embed_text(f"{query_text}\n{insight_text}")
        async with sessionmaker() as session:
            item = QueryEmbedding(
                user_id=self.user_id,
                connection_id=uuid.UUID(str(connection_id)),
                query_text=query_text,
                insight_text=insight_text,
                embedding=embedding,
            )
            session.add(item)
            await session.commit()

    async def search_similar(self, query_text: str, limit: int = 3) -> list[dict[str, Any]]:
        sessionmaker = get_sessionmaker()
        query_embedding = await self.embedder.embed_text(query_text)
        async with sessionmaker() as session:
            result = await session.execute(
                select(QueryEmbedding).where(QueryEmbedding.user_id == self.user_id)
            )
            rows = result.scalars().all()

        scored: list[dict[str, Any]] = []
        for row in rows:
            score = _cosine_similarity(query_embedding, row.embedding or [])
            scored.append(
                {
                    "query_text": row.query_text,
                    "insight_text": row.insight_text,
                    "score": round(score, 4),
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:limit]
