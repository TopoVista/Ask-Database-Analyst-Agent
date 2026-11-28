"""PostgreSQL-compatible durable queue with lease fencing.

The claim transaction is intentionally short. Workers execute outside it and
must present their lease owner and fencing token when publishing results.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrictrace import DurableJob

TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED"}
RETRYABLE = {"transient", "storage_unavailable", "worker_interrupted", "resource_exhausted"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StaleLeaseError(RuntimeError):
    pass


class DurableJobQueue:
    def __init__(self, db: AsyncSession, lease_seconds: int = 30):
        self.db = db
        self.lease_seconds = lease_seconds

    async def enqueue(self, workspace_id: UUID, job_type: str, payload: dict, idempotency_key: str, *, parent_job_id: UUID | None = None, max_attempts: int = 3, priority: int = 100) -> DurableJob:
        existing = await self.db.execute(select(DurableJob).where(DurableJob.workspace_id == workspace_id, DurableJob.idempotency_key == idempotency_key))
        job = existing.scalars().first()
        if job:
            return job
        job = DurableJob(workspace_id=workspace_id, parent_job_id=parent_job_id, job_type=job_type, input_payload=payload, idempotency_key=idempotency_key, max_attempts=max_attempts, priority=priority)
        self.db.add(job)
        await self.db.flush()
        return job

    async def claim(self, worker_id: str) -> DurableJob | None:
        now = utcnow()
        candidate = (
            select(DurableJob)
            .where(or_(
                DurableJob.status.in_(["QUEUED", "RETRY_WAIT"]),
                (DurableJob.status == "RUNNING") & (DurableJob.lease_expires_at < now),
            ), DurableJob.scheduled_at <= now, DurableJob.cancellation_requested.is_(False))
            .order_by(DurableJob.priority.asc(), DurableJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        result = await self.db.execute(candidate)
        job = result.scalars().first()
        if not job:
            return None
        job.status = "RUNNING"
        job.attempt_count += 1
        job.fencing_token += 1
        job.lease_owner = worker_id
        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=self.lease_seconds)
        job.started_at = job.started_at or now
        await self.db.flush()
        return job

    async def renew(self, job_id: UUID, worker_id: str, fencing_token: int) -> DurableJob:
        job = await self._owned(job_id, worker_id, fencing_token)
        job.heartbeat_at = utcnow()
        job.lease_expires_at = job.heartbeat_at + timedelta(seconds=self.lease_seconds)
        await self.db.flush()
        return job

    async def succeed(self, job_id: UUID, worker_id: str, fencing_token: int, result_reference: dict | None = None) -> DurableJob:
        job = await self._owned(job_id, worker_id, fencing_token)
        job.status, job.result_reference, job.finished_at = "SUCCEEDED", result_reference, utcnow()
        job.lease_owner, job.lease_expires_at = None, None
        await self.db.flush()
        return job

    async def fail(self, job_id: UUID, worker_id: str, fencing_token: int, category: str, message: str) -> DurableJob:
        job = await self._owned(job_id, worker_id, fencing_token)
        job.error = {"category": category, "message": message}
        if category in RETRYABLE and job.attempt_count < job.max_attempts:
            delay = min(300, 2 ** job.attempt_count) + random.uniform(0, 1)
            job.status, job.scheduled_at = "RETRY_WAIT", utcnow() + timedelta(seconds=delay)
        else:
            job.status, job.finished_at = "FAILED", utcnow()
        job.lease_owner, job.lease_expires_at = None, None
        await self.db.flush()
        return job

    async def cancel(self, job: DurableJob) -> None:
        job.cancellation_requested = True
        if job.status not in TERMINAL:
            job.status, job.finished_at = "CANCELLED", utcnow()
            job.lease_owner, job.lease_expires_at = None, None
        await self.db.flush()

    async def _owned(self, job_id: UUID, worker_id: str, fencing_token: int) -> DurableJob:
        job = await self.db.get(DurableJob, job_id, with_for_update=True)
        now = utcnow()
        expires_at = job.lease_expires_at if job else None
        # SQLite returns naive timestamps even for timezone-aware columns;
        # PostgreSQL retains the offset. Treat SQLite's stored value as UTC so
        # local tests exercise the same lease semantics.
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if not job or job.cancellation_requested or job.status != "RUNNING" or job.lease_owner != worker_id or job.fencing_token != fencing_token or not expires_at or expires_at <= now:
            raise StaleLeaseError("Worker lease is no longer authoritative.")
        return job
