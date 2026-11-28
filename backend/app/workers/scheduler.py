"""Persistent, bounded scheduler for due MetricTrace capture jobs."""
from __future__ import annotations

import asyncio

from app.config import get_settings
from app.models.database import get_sessionmaker
from app.services.metrictrace_service import MetricTraceService


class MetricTraceScheduler:
    async def run_once(self) -> int:
        async with get_sessionmaker()() as db:
            count = await MetricTraceService(db).enqueue_scheduled_postgres_captures()
            await db.commit()
            return count

    async def run_forever(self) -> None:
        poll_seconds = get_settings().metrictrace_scheduler_poll_seconds
        while True:
            await self.run_once()
            await asyncio.sleep(poll_seconds)


def main() -> None:
    asyncio.run(MetricTraceScheduler().run_forever())


if __name__ == "__main__":
    main()
