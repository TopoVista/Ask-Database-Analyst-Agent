from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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


class CaptureTableRequest(BaseModel):
    schema_name: str = Field(validation_alias="schema", serialization_alias="schema", min_length=1, max_length=63)
    table: str = Field(min_length=1, max_length=63)


class PostgresSourceCreate(BaseModel):
    workspace_id: str
    connection_id: str
    name: str = Field(min_length=1, max_length=255)
    tables: list[CaptureTableRequest] = Field(min_length=1, max_length=64)


class CaptureRead(BaseModel):
    dataset_version_id: str
    status: str
    row_count: int
    byte_size: int
    manifest_uri: str


class StaticLineageRequest(BaseModel):
    """A text-only, workspace-authorized static SQL inspection request."""

    workspace_id: str
    sql: str = Field(min_length=1, max_length=100_000)
    tables: list[str] = Field(min_length=1, max_length=64)
