from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.database import Base
from app.services.connection_service import ConnectionService
from app.models.connection import DBConnection
from app.models.query_embedding import QueryEmbedding
from app.models.session import QuerySession
from app.models.user import User


def test_describe_connection_error_for_invalid_password():
    message = ConnectionService.describe_connection_error(
        "asyncpg.exceptions.InvalidPasswordError: password authentication failed for user 'neondb_owner'"
    )

    assert "Database authentication failed" in message
    assert "Neon" in message


@pytest.mark.asyncio
async def test_validate_connection_payload_raises_friendly_message(monkeypatch):
    async def fake_execute(self, connection_string: str, sql: str, timeout: float = 30.0):
        return {
            "success": False,
            "error": "password authentication failed for user 'neondb_owner'",
            "rows": [],
            "columns": [],
            "row_count": 0,
            "execution_time_ms": 1,
        }

    monkeypatch.setattr("app.services.connection_service.SQLExecutor.execute", fake_execute)

    service = ConnectionService()
    payload = SimpleNamespace(
        name="Neon",
        db_type="postgresql",
        host="example.neon.tech",
        port=5432,
        database_name="neondb",
        username="neondb_owner",
        password="wrong-password",
        ssl_mode="require",
    )

    with pytest.raises(ValueError, match="Database authentication failed"):
        await service.validate_connection_payload(payload)


def test_build_connection_string_includes_real_password():
    service = ConnectionService()
    conn = DBConnection(
        name="Neon",
        db_type="postgresql",
        host="example.neon.tech",
        port=5432,
        database_name="neondb",
        username="neondb_owner",
        password_encrypted=service.encryption.encrypt("secret-password"),
        ssl_mode="require",
        is_active=True,
    )

    connection_string = service.build_connection_string(conn)

    assert "secret-password" in connection_string
    assert "***" not in connection_string


@pytest.mark.asyncio
async def test_delete_connection_removes_related_embeddings_and_sessions():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    user_id = uuid4()
    connection_id = uuid4()

    async with Session() as session:
        user = User(
            id=user_id,
            clerk_id="clerk-test-user",
            email="test@example.com",
            name="Test User",
        )
        connection = DBConnection(
            id=connection_id,
            user_id=user_id,
            name="Test connection",
            db_type="postgresql",
            host="example.neon.tech",
            port=5432,
            database_name="neondb",
            username="neondb_owner",
            password_encrypted="encrypted",
            ssl_mode="require",
            is_active=True,
        )
        query_session = QuerySession(
            user_id=user_id,
            connection_id=connection_id,
            title="Session",
        )
        embedding = QueryEmbedding(
            user_id=user_id,
            connection_id=connection_id,
            query_text="how many users?",
            insight_text="one user",
            embedding=[0.1, 0.2],
        )

        session.add_all([user, connection, query_session, embedding])
        await session.commit()

    async with Session() as session:
        service = ConnectionService(session)
        deleted = await service.delete_connection(connection_id, user_id)
        await session.commit()
        assert deleted is True

        remaining_connection = await session.get(DBConnection, connection_id)
        remaining_embeddings = (await session.execute(select(QueryEmbedding))).scalars().all()
        remaining_sessions = (await session.execute(select(QuerySession))).scalars().all()

        assert remaining_connection is None
        assert remaining_embeddings == []
        assert remaining_sessions == []

    await engine.dispose()
