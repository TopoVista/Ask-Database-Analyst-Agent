from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    connection_id: UUID
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    query_count: int | None = None
