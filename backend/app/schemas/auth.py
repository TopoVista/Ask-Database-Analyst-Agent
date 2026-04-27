from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuthenticatedUser(BaseModel):
    clerk_id: str
    email: str
    name: str | None = None


class AppUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clerk_id: str
    email: str
    name: str | None = None
