"""MetricTrace deterministic replay endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.dependencies import get_current_user, get_db
from app.schemas.auth import AuthenticatedUser
from app.infrastructure.capture import CaptureTable, SnapshotCaptureError
from app.models.metrictrace import DurableJob, ReplayCell, ReplayJob
from app.schemas.metrictrace import ContractCreateRequest, ContractEvaluateRequest, DatasetDiffRequest, JoinAuditRequest, MetricPromotionRequest, PostgresDiscoveryRequest, PostgresSourceCreate, RegressionPolicyCreateRequest, ReplayRequest, ShadowExecutionRequest, SqlRegressionRequest, StaticLineageRequest
from metrictrace_sdk.lineage import LineageError
from metrictrace_sdk.dataset_diff import DatasetDiffError
from metrictrace_sdk.regression import RegressionError
from metrictrace_sdk.join_audit import JoinAuditError
from metrictrace_sdk.contracts import ContractError
from app.services.metrictrace_service import MetricTraceService
from app.services.user_service import ensure_user

router = APIRouter(prefix="/metrictrace", tags=["metrictrace"])


@router.post("/replays/{replay_id}/decision-receipt", status_code=status.HTTP_201_CREATED)
async def create_decision_receipt(replay_id: UUID, current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    """Create or retrieve an integrity-checkable receipt for a completed replay."""
    user = await ensure_user(db, current_user)
    try:
        return await MetricTraceService(db).create_decision_receipt(user, replay_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/decision-receipts/{receipt_id}")
async def get_decision_receipt(receipt_id: UUID, current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    try:
        return await MetricTraceService(db).decision_receipt_for_user(user, receipt_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/regression-policies", status_code=status.HTTP_201_CREATED)
async def create_regression_policy(
    request: RegressionPolicyCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    user = await ensure_user(db, current_user)
    try:
        policy = await MetricTraceService(db).create_regression_policy(
            user, UUID(request.workspace_id), request.name, request.max_absolute_difference,
            request.max_percent_difference,
            UUID(request.required_contract_id) if request.required_contract_id else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (RegressionError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"policy_id": str(policy.id), "version": policy.version, "definition_hash": policy.definition_hash}


@router.post("/shadow-executions", status_code=status.HTTP_201_CREATED)
async def execute_shadow_run(
    request: ShadowExecutionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Explicitly run candidate SQL under an immutable persisted gate policy."""
    user = await ensure_user(db, current_user)
    try:
        return await MetricTraceService(db).execute_shadow_run(
            user, UUID(request.workspace_id), UUID(request.policy_id), UUID(request.baseline_definition_id),
            UUID(request.candidate_definition_id), UUID(request.dataset_version_id),
            CaptureTable(request.table.schema_name, request.table.table) if request.table else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ContractError, DatasetDiffError, RegressionError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/metric-definitions/{definition_id}/promotions", status_code=status.HTTP_201_CREATED)
async def promote_metric_definition(
    definition_id: UUID,
    request: MetricPromotionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Consume one PASS shadow record to atomically activate a candidate definition."""
    user = await ensure_user(db, current_user)
    try:
        return await MetricTraceService(db).promote_metric_definition(
            user, UUID(request.workspace_id), definition_id, UUID(request.shadow_execution_id)
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/contracts", status_code=status.HTTP_201_CREATED)
async def create_contract(
    request: ContractCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Create a new immutable version; updating a contract creates another version."""
    user = await ensure_user(db, current_user)
    try:
        contract = await MetricTraceService(db).create_contract(
            user, UUID(request.workspace_id), request.name, request.contracts
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ContractError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"contract": MetricTraceService._contract_read(contract)}


@router.get("/contracts")
async def list_contracts(
    workspace_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    user = await ensure_user(db, current_user)
    try:
        contracts = await MetricTraceService(db).contracts_for_user(user, workspace_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"contracts": contracts}


@router.post("/contracts/{contract_id}/evaluations", status_code=status.HTTP_201_CREATED)
async def evaluate_contract(
    contract_id: UUID,
    request: ContractEvaluateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Explicitly authorize a state-changing historical contract evaluation."""
    user = await ensure_user(db, current_user)
    try:
        return await MetricTraceService(db).evaluate_contract_for_version(
            user, UUID(request.workspace_id), contract_id, UUID(request.dataset_version_id)
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ContractError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/sources/postgresql/discover")
async def discover_postgres_tables(
    request: PostgresDiscoveryRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Discover only capture-compatible tables for one owned connection."""
    user = await ensure_user(db, current_user)
    try:
        tables = await MetricTraceService(db).discover_postgres_tables(
            user, UUID(request.workspace_id), UUID(request.connection_id)
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (SnapshotCaptureError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"tables": tables}


@router.get("/sources")
async def list_metric_sources(
    workspace_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    user = await ensure_user(db, current_user)
    try:
        sources = await MetricTraceService(db).sources_for_user(user, workspace_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"sources": sources}


@router.post("/dataset-diff")
async def compare_dataset_versions(
    request: DatasetDiffRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Compare two authorized immutable dataset versions via the shared SDK core."""
    user = await ensure_user(db, current_user)
    try:
        return await MetricTraceService(db).compare_dataset_versions(
            user,
            UUID(request.workspace_id),
            UUID(request.old_version_id),
            UUID(request.new_version_id),
            request.key_columns,
            old_table=CaptureTable(request.old_table.schema_name, request.old_table.table) if request.old_table else None,
            new_table=CaptureTable(request.new_table.schema_name, request.new_table.table) if request.new_table else None,
            limit=request.limit,
            offset=request.offset,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (DatasetDiffError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/sql-regression")
async def check_sql_regression(
    request: SqlRegressionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Evaluate baseline and candidate read-only SQL on one immutable version."""
    user = await ensure_user(db, current_user)
    try:
        return await MetricTraceService(db).check_sql_regression_for_version(
            user,
            UUID(request.workspace_id),
            UUID(request.dataset_version_id),
            request.baseline_sql,
            request.candidate_sql,
            table=CaptureTable(request.table.schema_name, request.table.table) if request.table else None,
            max_absolute_difference=request.max_absolute_difference,
            max_percent_difference=request.max_percent_difference,
            parameters=request.parameters,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (RegressionError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/join-audit")
async def audit_sql_joins(
    request: JoinAuditRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Run the shared cardinality diagnostic on one authorized snapshot."""
    user = await ensure_user(db, current_user)
    try:
        return await MetricTraceService(db).audit_sql_joins_for_version(
            user, UUID(request.workspace_id), UUID(request.dataset_version_id), request.sql
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (JoinAuditError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"replay_id": str(job.id), "status": job.status, "attribution": job.attribution}


@router.get("/replay-workspace")
async def replay_workspace(current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    """Discover the caller's authorized workspace without creating sample data."""
    user = await ensure_user(db, current_user)
    return await MetricTraceService(db).replay_workspace_for_user(user)


@router.get("/replay-options")
async def replay_options(workspace_id: UUID, current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    try:
        return await MetricTraceService(db).replay_options_for_user(user, workspace_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/replays/{replay_id}")
async def get_replay(replay_id: UUID, current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    service = MetricTraceService(db)
    replay = await db.get(ReplayJob, replay_id)
    if not replay:
        raise HTTPException(status_code=404, detail="Replay not found")
    await service._owned_workspace(user, replay.workspace_id)
    rows = list(
        (
            await db.execute(
                select(ReplayCell, DurableJob)
                .outerjoin(DurableJob, ReplayCell.durable_job_id == DurableJob.id)
                .where(ReplayCell.replay_job_id == replay.id)
                .order_by(ReplayCell.label)
            )
        ).all()
    )
    return {
        "replay_id": str(replay.id),
        "status": replay.status,
        "attribution": replay.attribution,
        "cells": [
            {
                "id": str(cell.id),
                "label": cell.label,
                "status": cell.status,
                "result_inr": cell.result_text,
                "error": cell.error,
                "duration_ms": cell.duration_ms,
                "job_id": str(cell.durable_job_id) if cell.durable_job_id else None,
                "retryable": durable is not None and durable.status == "RETRY_WAIT",
            }
            for cell, durable in rows
        ],
    }


@router.delete("/replays/{replay_id}", status_code=status.HTTP_202_ACCEPTED)
async def cancel_replay(replay_id: UUID, current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    try:
        replay = await MetricTraceService(db).cancel_replay(user, replay_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"replay_id": str(replay.id), "status": replay.status}
