from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, get_db
from app.schemas.auth import AppUserRead, AuthenticatedUser
from app.services.user_service import ensure_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=AppUserRead)
async def me(current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    return user

