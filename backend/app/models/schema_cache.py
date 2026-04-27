from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class SchemaCache(Base):
    __tablename__ = "schema_cache"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("db_connections.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    schema_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    table_count: Mapped[int | None] = mapped_column(Integer)
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


Index("idx_schema_cache_connection", SchemaCache.connection_id, unique=True)

