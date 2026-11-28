"""MetricTrace deterministic replay endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.dependencies import get_current_user, get_db
from app.schemas.auth import AuthenticatedUser
from app.infrastructure.capture import CaptureTable, SnapshotCaptureError
from app.models.metrictrace import ReplayCell, ReplayJob
from app.schemas.metrictrace import PostgresSourceCreate, ReplayRequest, StaticLineageRequest
from metrictrace_sdk.lineage import LineageError
from app.services.metrictrace_service import MetricTraceService
from app.services.user_service import ensure_user

router = APIRouter(prefix="/metrictrace", tags=["metrictrace"])


@router.post("/lineage/inspect")
async def inspect_static_lineage(
    request: StaticLineageRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Inspect static SQL dependencies using the SDK implementation after workspace isolation."""
    user = await ensure_user(db, current_user)
    try:
        lineage = await MetricTraceService(db).inspect_static_lineage(
            user, UUID(request.workspace_id), request.sql, request.tables
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (LineageError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"lineage": lineage}


@router.post("/sources/postgresql", status_code=status.HTTP_201_CREATED)
async def create_postgres_source(request: PostgresSourceCreate, current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    try:
        source = await MetricTraceService(db).create_postgres_source(
            user,
            UUID(request.workspace_id),
            UUID(request.connection_id),
            request.name,
            [CaptureTable(schema=table.schema_name, table=table.table) for table in request.tables],
            request.schedule_seconds,
        )
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"source_id": str(source.id), "status": source.capture_status, "source_type": source.source_type}


@router.post("/sources/{source_id}/captures", status_code=status.HTTP_202_ACCEPTED)
async def capture_postgres_source(source_id: UUID, workspace_id: UUID, current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    try:
        job = await MetricTraceService(db).enqueue_postgres_capture(user, workspace_id, source_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ValueError, SnapshotCaptureError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"job_id": str(job.id), "status": job.status, "source_id": str(source_id)}


@router.get("/sources/{source_id}/captures/{job_id}")
async def get_postgres_capture(source_id: UUID, job_id: UUID, workspace_id: UUID, current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    try:
        job = await MetricTraceService(db).capture_job_for_user(user, workspace_id, source_id, job_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"job_id": str(job.id), "source_id": str(source_id), "status": job.status, "error": job.error, "result": job.result_reference}


@router.post("/demo")
async def run_demo(current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    try:
        return await MetricTraceService(db).demo(user)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/replays", status_code=status.HTTP_202_ACCEPTED)
async def create_replay(request: ReplayRequest, current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    try:
        job = await MetricTraceService(db).submit_replay(
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


@router.get("/replays/{replay_id}")
async def get_replay(replay_id: UUID, current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    service = MetricTraceService(db)
    replay = await db.get(ReplayJob, replay_id)
    if not replay:
        raise HTTPException(status_code=404, detail="Replay not found")
    await service._owned_workspace(user, replay.workspace_id)
    cells = list((await db.execute(select(ReplayCell).where(ReplayCell.replay_job_id == replay.id).order_by(ReplayCell.label))).scalars())
    return {"replay_id": str(replay.id), "status": replay.status, "attribution": replay.attribution, "cells": [{"id": str(c.id), "label": c.label, "status": c.status, "result_inr": c.result_text, "error": c.error, "duration_ms": c.duration_ms, "job_id": str(c.durable_job_id) if c.durable_job_id else None} for c in cells]}
