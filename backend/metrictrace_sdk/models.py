from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FourWayReplayRequest:
    workspace_id: str
    old_version_id: str
    new_version_id: str
    old_definition_id: str
    new_definition_id: str


@dataclass(frozen=True)
class ReplayResult:
    replay_id: str
    status: str
    attribution: dict[str, Any] | None


@dataclass(frozen=True)
class StaticLineageRequest:
    workspace_id: str
    sql: str
    tables: list[str]


@dataclass(frozen=True)
class StaticLineageResult:
    lineage: dict[str, Any]
