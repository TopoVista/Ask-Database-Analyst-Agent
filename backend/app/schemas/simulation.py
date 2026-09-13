from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SimulationParameters(BaseModel):
    # Keep scenario-specific values (for example `price_change_pct`) instead
    # of silently discarding them during request validation.
    model_config = ConfigDict(extra="allow")
    variable: str | None = None
    change_type: str | None = None
    change_value: float | int | None = None
    affected_scope: str | None = None


class SimulationRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    connection_id: str
    parameters: SimulationParameters
    session_id: str | None = None
