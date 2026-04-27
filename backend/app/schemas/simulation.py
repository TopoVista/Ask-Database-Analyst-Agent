from __future__ import annotations

from pydantic import BaseModel


class SimulationParameters(BaseModel):
    variable: str | None = None
    change_type: str | None = None
    change_value: float | int | None = None
    affected_scope: str | None = None


class SimulationRequest(BaseModel):
    question: str
    connection_id: str
    parameters: SimulationParameters
    session_id: str | None = None

