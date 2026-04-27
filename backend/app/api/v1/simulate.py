from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.simulation_agent import SimulationAgent
from app.dependencies import get_current_user, get_db
from app.schemas.auth import AuthenticatedUser
from app.schemas.simulation import SimulationRequest
from app.services.connection_service import ConnectionService
from app.services.llm_service import LLMService
from app.services.user_service import ensure_user

router = APIRouter(prefix="/simulate", tags=["simulation"])


@router.post("/what-if")
async def run_simulation(
    request: SimulationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    user = await ensure_user(db, current_user)
    conn_service = ConnectionService(db)
    connection_string = await conn_service.get_decrypted_connection_string(request.connection_id, user.id)
    if not connection_string:
        raise HTTPException(status_code=404, detail="Connection not found")

    sim_agent = SimulationAgent(LLMService())

    async def stream():
        async for event in sim_agent.run(
            question=request.question,
            parameters=request.parameters.model_dump(),
            connection_string=connection_string,
        ):
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")

