from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, JSON
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class QueryHistory(Base):
    __tablename__ = "query_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("query_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=False, index=True
    )
    user_question: Mapped[str] = mapped_column(Text, nullable=False)
    intent_type: Mapped[str | None] = mapped_column(String(100))
    task_plan: Mapped[dict | None] = mapped_column(JSON)
    generated_queries: Mapped[list | None] = mapped_column(JSON)
    analysis_result: Mapped[dict | None] = mapped_column(JSON)
    hypotheses: Mapped[list | None] = mapped_column(JSON)
    final_insight: Mapped[str | None] = mapped_column(Text)
    anomalies_detected: Mapped[list | None] = mapped_column(JSON)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    total_tokens_used: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


Index("idx_history_session_id", QueryHistory.session_id)
Index("idx_history_user_id", QueryHistory.user_id)
Index("idx_history_created_at", QueryHistory.created_at)

