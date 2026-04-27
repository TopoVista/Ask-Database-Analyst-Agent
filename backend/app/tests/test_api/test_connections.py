from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_connections_requires_auth():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/connections")
    assert response.status_code == 401

