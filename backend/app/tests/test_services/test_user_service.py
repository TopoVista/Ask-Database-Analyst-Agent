from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.middleware.auth import _parse_clerk_payload
from app.models.database import Base
from app.models.user import User
from app.schemas.auth import AuthenticatedUser
from app.services.user_service import ensure_user


def test_parse_clerk_payload_uses_unique_fallback_email():
    user = _parse_clerk_payload({"sub": "user_123"})

    assert user.clerk_id == "user_123"
    assert user.email == "user_123@users.invalid"


@pytest.mark.asyncio
async def test_ensure_user_keeps_existing_real_email_when_auth_email_is_placeholder():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    user_id = uuid4()

    async with Session() as session:
        session.add(
            User(
                id=user_id,
                clerk_id="user_123",
                email="real@example.com",
                name="Original Name",
            )
        )
        await session.commit()

    async with Session() as session:
        user = await ensure_user(
            session,
            AuthenticatedUser(clerk_id="user_123", email="user_123@users.invalid", name="Updated Name"),
        )
        await session.commit()

        assert user.email == "real@example.com"
        assert user.name == "Updated Name"

    await engine.dispose()
