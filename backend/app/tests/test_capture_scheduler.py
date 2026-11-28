from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.connection import DBConnection
from app.models.database import get_sessionmaker
from app.models.metrictrace import DurableJob, MetricSource, Workspace
from app.models.user import User
from app.services.metrictrace_service import MetricTraceService


@pytest.mark.asyncio
async def test_scheduler_queues_one_capture_per_source_time_window(client):
    workspace_id = uuid4()
    source_id = uuid4()
    async with get_sessionmaker()() as db:
        user = User(clerk_id=f"scheduler-{uuid4()}", email=f"scheduler-{uuid4()}@example.test")
        db.add(user)
        await db.flush()
        connection = DBConnection(
            user_id=user.id,
            name="source",
            db_type="postgresql",
            host="db.example.test",
            database_name="source",
            username="reader",
            password_encrypted="opaque",
            is_active=True,
        )
        db.add_all([Workspace(id=workspace_id, name="scheduled"), connection])
        await db.flush()
        source = MetricSource(
            id=source_id,
            workspace_id=workspace_id,
            connection_id=connection.id,
            name="orders",
            source_type="postgresql",
            capture_config={
                "tables": [{"schema": "public", "table": "orders"}],
                "schedule_seconds": 300,
            },
            capture_status="ready",
        )
        db.add(source)
        await db.commit()

    now = datetime(2026, 11, 28, 0, 5, tzinfo=timezone.utc)
    async with get_sessionmaker()() as db:
        service = MetricTraceService(db)
        assert await service.enqueue_scheduled_postgres_captures(now) == 1
        await db.commit()

    async with get_sessionmaker()() as db:
        service = MetricTraceService(db)
        assert await service.enqueue_scheduled_postgres_captures(now) == 0
        jobs = (await db.execute(select(DurableJob).where(DurableJob.workspace_id == workspace_id))).scalars().all()
        source = await db.get(MetricSource, source_id)
        assert len(jobs) == 1
        assert jobs[0].input_payload == {"source_id": str(source_id), "scheduled": True}
        assert source.capture_status == "queued"
