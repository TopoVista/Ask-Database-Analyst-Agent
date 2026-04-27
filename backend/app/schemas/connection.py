from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConnectionCreate(BaseModel):
    name: str
    db_type: str = "postgresql"
    host: str
    port: int = 5432
    database_name: str
    username: str
    password: str = Field(min_length=1)
    ssl_mode: str = "prefer"


class ConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    db_type: str
    host: str
    port: int
    database_name: str
    username: str
    ssl_mode: str
    is_active: bool
    last_tested_at: datetime | None = None
    created_at: datetime


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
