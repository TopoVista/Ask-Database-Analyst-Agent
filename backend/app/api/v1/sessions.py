from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.dependencies import get_current_user, get_db
from app.models.query_history import QueryHistory
from app.models.session import QuerySession
from app.schemas.auth import AuthenticatedUser
from app.schemas.session import SessionRead
from app.services.user_service import ensure_user

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionRead])
async def list_sessions(current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    result = await db.execute(
        select(
            QuerySession,
            func.count(QueryHistory.id).label("query_count"),
        )
        .outerjoin(QueryHistory, QueryHistory.session_id == QuerySession.id)
        .where(QuerySession.user_id == user.id)
        .group_by(QuerySession.id)
        .order_by(QuerySession.created_at.desc())
    )
    sessions: list[SessionRead] = []
    for session, query_count in result.all():
        data = SessionRead.model_validate(session)
        sessions.append(data.model_copy(update={"query_count": int(query_count or 0)}))
    return sessions


@router.get("/{session_id}")
async def get_session(session_id: str, current_user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)):
    user = await ensure_user(db, current_user)
    session = await db.get(QuerySession, session_id)
    if session is None or str(session.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Session not found")
    result = await db.execute(select(QueryHistory).where(QueryHistory.session_id == session.id).order_by(QueryHistory.created_at.asc()))
    history = result.scalars().all()
    return {"session": session, "history": history}

