"""MetricTrace replay-cell worker using durable queue ownership."""
from __future__ import annotations

import asyncio
import contextlib
from uuid import UUID

from app.models.database import get_sessionmaker
from app.services.job_queue import DurableJobQueue, StaleLeaseError
from app.services.metrictrace_service import MetricTraceService
from app.workers.runner import Worker


class MetricTraceWorker(Worker):
    def __init__(self, worker_id: str = ""):
        super().__init__({}, worker_id)

    async def _heartbeat(self, job_id: UUID, fencing_token: int) -> None:
        """Renew independently, so source execution never retains queue locks."""
        while True:
            await asyncio.sleep(max(1, self.lease_seconds // 3))
            try:
                async with get_sessionmaker()() as db:
                    await DurableJobQueue(db, self.lease_seconds).renew(job_id, self.worker_id, fencing_token)
                    await db.commit()
            except StaleLeaseError:
                return

    async def run_once(self) -> bool:
        # Claim and commit in a short transaction. Long source queries and
        # DuckDB execution must never retain the PostgreSQL queue lock.
        async with get_sessionmaker()() as db:
            queue = DurableJobQueue(db, self.lease_seconds)
            job = await queue.claim(self.worker_id)
            if not job:
                await db.commit()
                return False
            job_id, workspace_id, job_type, payload, fencing_token = job.id, job.workspace_id, job.job_type, dict(job.input_payload), job.fencing_token
            await db.commit()

        heartbeat = asyncio.create_task(self._heartbeat(job_id, fencing_token))
        async with get_sessionmaker()() as db:
            queue = DurableJobQueue(db, self.lease_seconds)
            try:
                if job_type == "REPLAY_CELL_EXECUTION":
                    result = await MetricTraceService(db).execute_queued_cell(UUID(payload["cell_id"]), queue, self.worker_id, fencing_token)
                elif job_type == "SNAPSHOT_CAPTURE":
                    version = await MetricTraceService(db).execute_postgres_capture(workspace_id, UUID(payload["source_id"]))
                    result = {"dataset_version_id": str(version.id), "manifest_uri": version.manifest_uri, "row_count": version.row_count}
                else:
                    await queue.fail(job_id, self.worker_id, fencing_token, "permanent", f"Unsupported job type {job_type}")
                    await db.commit()
                    return True
                await queue.succeed(job_id, self.worker_id, fencing_token, result)
                await db.commit()
            except StaleLeaseError:
                await db.rollback()
            except Exception as exc:
                await queue.fail(job_id, self.worker_id, fencing_token, "transient", str(exc))
                await db.commit()
            finally:
                heartbeat.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await heartbeat
            return True
