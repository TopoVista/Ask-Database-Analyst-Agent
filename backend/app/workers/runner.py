"""Small worker loop that keeps job ownership separate from execution."""

from __future__ import annotations

import asyncio
import socket
from collections.abc import Awaitable, Callable

from app.config import get_settings
from app.models.database import get_sessionmaker
from app.services.job_queue import DurableJobQueue, StaleLeaseError

JobHandler = Callable[[dict], Awaitable[dict | None]]


class Worker:
    def __init__(self, handlers: dict[str, JobHandler], worker_id: str = ""):
        settings = get_settings()
        self.handlers = handlers
        self.worker_id = worker_id or settings.metrictrace_worker_id or f"worker-{socket.gethostname()}"
        self.lease_seconds = settings.metrictrace_job_lease_seconds

    async def run_once(self) -> bool:
        async with get_sessionmaker()() as db:
            queue = DurableJobQueue(db, self.lease_seconds)
            job = await queue.claim(self.worker_id)
            if not job:
                await db.commit()
                return False
            job_id, token = job.id, job.fencing_token
            handler = self.handlers.get(job.job_type)
            if handler is None:
                await queue.fail(job_id, self.worker_id, token, "permanent", f"No handler for {job.job_type}")
                await db.commit()
                return True
            try:
                result = await handler(job.input_payload)
                await queue.succeed(job_id, self.worker_id, token, result)
            except StaleLeaseError:
                await db.rollback()
            except Exception as exc:
                await queue.fail(job_id, self.worker_id, token, "transient", str(exc))
            else:
                await db.commit()
            return True

    async def run_forever(self, idle_seconds: float = 1.0) -> None:
        while True:
            claimed = await self.run_once()
            if not claimed:
                await asyncio.sleep(idle_seconds)
