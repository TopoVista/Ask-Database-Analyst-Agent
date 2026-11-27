"""MetricTrace deterministic replay endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user, get_db
from app.schemas.auth import AuthenticatedUser
from app.schemas.metrictrace import ReplayRequest
from app.services.metrictrace_service import MetricTraceService
from app.services.user_service import ensure_user

router = APIRouter(prefix="/metrictrace", tags=["metrictrace"])


@router.post("/demo")
async def run_demo(current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    try:
        return await MetricTraceService(db).demo(user)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/replays")
async def create_replay(request: ReplayRequest, current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    try:
        job = await MetricTraceService(db).replay(
            user,
            UUID(request.workspace_id),
            UUID(request.old_version_id),
            UUID(request.new_version_id),
            UUID(request.old_definition_id),
            UUID(request.new_definition_id),
        )
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"replay_id": str(job.id), "status": job.status, "attribution": job.attribution}
