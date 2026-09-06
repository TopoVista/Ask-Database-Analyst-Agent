from __future__ import annotations

import os
import tempfile

_TMP_DIR = tempfile.mkdtemp(prefix="ada-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DIR}/test.db"
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("AUTH_BYPASS", "false")

import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.main import app
from app.models.database import Base, get_engine


@pytest.fixture
async def client(monkeypatch):
    """HTTP client with auth bypass enabled for API tests.

    The auth middleware calls get_settings() per request, so clearing the
    settings cache with AUTH_BYPASS=true scoped to this fixture (and
    clearing again on teardown) leaves the auth-required tests unaffected.

    Tables are created explicitly because AsyncClient(app=...) does not
    run the application startup lifespan (which creates the schema in
    production).
    """
    monkeypatch.setenv("AUTH_BYPASS", "true")
    get_settings.cache_clear()
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
    get_settings.cache_clear()
