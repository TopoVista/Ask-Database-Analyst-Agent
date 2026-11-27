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
