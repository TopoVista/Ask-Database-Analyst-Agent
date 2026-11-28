from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.metrictrace import DurableJob, Workspace
from app.services.job_queue import DurableJobQueue, StaleLeaseError, utcnow


@pytest.mark.asyncio
async def test_job_claim_is_idempotent_and_stale_worker_cannot_publish(client):
    # The client fixture leaves the session factory configured for its fresh DB.
    from app.models.database import get_sessionmaker
    async with get_sessionmaker()() as db:
        workspace = Workspace(name="queue test")
        db.add(workspace)
        await db.flush()
        queue = DurableJobQueue(db, lease_seconds=5)
        job = await queue.enqueue(workspace.id, "FOUR_WAY_REPLAY", {"replay_id": "x"}, "replay:x")
        same = await queue.enqueue(workspace.id, "FOUR_WAY_REPLAY", {"replay_id": "x"}, "replay:x")
        assert same.id == job.id
        claimed_a = await queue.claim("worker-a")
        assert claimed_a and claimed_a.fencing_token == 1
        claimed_a.lease_expires_at = utcnow() - timedelta(seconds=1)
        await db.flush()
        claimed_b = await queue.claim("worker-b")
        assert claimed_b and claimed_b.id == job.id and claimed_b.fencing_token == 2
        with pytest.raises(StaleLeaseError):
            await queue.succeed(job.id, "worker-a", 1)
        await queue.succeed(job.id, "worker-b", 2, {"ok": True})
        persisted = (await db.execute(select(DurableJob).where(DurableJob.id == job.id))).scalars().one()
        assert persisted.status == "SUCCEEDED"


@pytest.mark.asyncio
async def test_worker_interruption_retries_then_exhausts_without_reclaiming_terminal_job(client):
    from app.models.database import get_sessionmaker

    async with get_sessionmaker()() as db:
        workspace = Workspace(name="interruption test")
        db.add(workspace)
        await db.flush()
        queue = DurableJobQueue(db, lease_seconds=5)
        job = await queue.enqueue(
            workspace.id, "SNAPSHOT_CAPTURE", {"source_id": "x"}, "capture:x", max_attempts=2
        )

        first = await queue.claim("terminated-worker")
        assert first and first.id == job.id
        first_token = first.fencing_token
        await queue.fail(job.id, "terminated-worker", first_token, "worker_interrupted", "terminated")
        assert job.status == "RETRY_WAIT"
        job.scheduled_at = utcnow() - timedelta(seconds=1)
        await db.flush()

        second = await queue.claim("recovery-worker")
        assert second and second.id == job.id and second.fencing_token == first_token + 1
        await queue.fail(job.id, "recovery-worker", second.fencing_token, "worker_interrupted", "terminated again")
        assert job.status == "FAILED"
        assert await queue.claim("third-worker") is None


@pytest.mark.asyncio
async def test_cancelled_job_fences_a_worker_that_already_claimed_it(client):
    from app.models.database import get_sessionmaker

    async with get_sessionmaker()() as db:
        workspace = Workspace(name="cancellation fencing test")
        db.add(workspace)
        await db.flush()
        queue = DurableJobQueue(db, lease_seconds=5)
        job = await queue.enqueue(workspace.id, "SNAPSHOT_CAPTURE", {"source_id": "x"}, "capture:cancel")
        claimed = await queue.claim("worker-a")
        assert claimed is not None

        await queue.cancel(job)
        assert job.status == "CANCELLED"
        with pytest.raises(StaleLeaseError):
            await queue.succeed(job.id, "worker-a", claimed.fencing_token, {"published": True})
