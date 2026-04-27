from __future__ import annotations

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(url: str) -> dict:
    kwargs: dict = {"future": True, "echo": get_settings().environment == "development"}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs.update({"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10})
    return kwargs


@lru_cache
def get_engine():
    settings = get_settings()
    return create_async_engine(settings.database_url, **_engine_kwargs(settings.database_url))


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async_session = get_sessionmaker()
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

