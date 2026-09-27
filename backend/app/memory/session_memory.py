"""Persistent, bounded conversation context backed by query history."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.database import get_sessionmaker
from app.models.query_history import QueryHistory


class SessionMemory:
    """Read recent completed turns from the application's existing database.

    Query history is written by the query endpoint after each completed run, so
    it survives Render restarts without Redis or local files.
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = UUID(str(session_id))

    async def get_history(self, limit: int = 20) -> list[str]:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            result = await session.execute(
                select(QueryHistory.user_question, QueryHistory.final_insight)
                .where(QueryHistory.session_id == self.session_id, QueryHistory.error.is_(None))
                .order_by(QueryHistory.created_at.desc())
                .limit(limit)
            )
        return [
            f"Q: {question}\nA: {insight}"
            for question, insight in reversed(result.all())
            if insight
        ]

    async def add_entry(self, question: str, insight: str) -> None:
        """Retained for the pipeline interface; the endpoint persists the turn."""
        del question, insight
