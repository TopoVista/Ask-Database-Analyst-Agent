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
    schedule_seconds: int | None = Field(default=None, ge=300, le=2_592_000)


class PostgresDiscoveryRequest(BaseModel):
    workspace_id: str
    connection_id: str


class DatasetDiffRequest(BaseModel):
    workspace_id: str
    old_version_id: str
    new_version_id: str
    key_columns: list[str] = Field(default_factory=list, max_length=16)
    old_table: CaptureTableRequest | None = None
    new_table: CaptureTableRequest | None = None
    limit: int = Field(default=100, ge=1, le=1_000)
    offset: int = Field(default=0, ge=0)


class SqlRegressionRequest(BaseModel):
    workspace_id: str
    dataset_version_id: str
    baseline_sql: str = Field(min_length=1, max_length=100_000)
    candidate_sql: str = Field(min_length=1, max_length=100_000)
    table: CaptureTableRequest | None = None
    max_absolute_difference: str | None = Field(default=None, max_length=128)
    max_percent_difference: str | None = Field(default=None, max_length=128)
    parameters: dict[str, str | int | float | bool | None] = Field(default_factory=dict, max_length=32)


class JoinAuditRequest(BaseModel):
    workspace_id: str
    dataset_version_id: str
    sql: str = Field(min_length=1, max_length=100_000)


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
