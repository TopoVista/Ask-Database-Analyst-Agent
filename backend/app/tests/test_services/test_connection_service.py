from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.connection_service import ConnectionService
from app.models.connection import DBConnection


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
