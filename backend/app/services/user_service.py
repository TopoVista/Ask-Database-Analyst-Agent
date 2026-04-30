from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import AuthenticatedUser


def _is_placeholder_email(email: str | None) -> bool:
    if not email:
        return True
    lowered = email.lower()
    return lowered == "unknown@example.com" or lowered.endswith("@users.invalid")


async def ensure_user(db: AsyncSession, current_user: AuthenticatedUser) -> User:
    result = await db.execute(select(User).where(User.clerk_id == current_user.clerk_id))
    user = result.scalar_one_or_none()
    if user is not None:
        if not (_is_placeholder_email(current_user.email) and not _is_placeholder_email(user.email)):
            user.email = current_user.email
        user.name = current_user.name
        await db.flush()
        return user

    user = User(clerk_id=current_user.clerk_id, email=current_user.email, name=current_user.name)
    db.add(user)
    await db.flush()
    return user
