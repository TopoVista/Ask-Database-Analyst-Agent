from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ReplayRequest(BaseModel):
    workspace_id: str
    old_version_id: str
    new_version_id: str
    old_definition_id: str
    new_definition_id: str


class ReplayRead(BaseModel):
    replay_id: str
    status: str
    cells: list[dict[str, Any]]
    attribution: dict[str, Any] | None = None
