from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user, get_db
from app.schemas.auth import AuthenticatedUser
from app.schemas.connection import ConnectionCreate, ConnectionRead, ConnectionTestResponse
from app.services.connection_service import ConnectionService
from app.services.user_service import ensure_user

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("", response_model=list[ConnectionRead])
async def list_connections(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    user = await ensure_user(db, current_user)
    service = ConnectionService(db)
    connections = await service.list_connections(user.id)
    return connections


@router.post("", response_model=ConnectionRead)
async def create_connection(
    request: ConnectionCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    user = await ensure_user(db, current_user)
    service = ConnectionService(db)
    conn = await service.create_connection(user.id, request)
    return conn


@router.post("/{connection_id}/test", response_model=ConnectionTestResponse)
async def test_connection(
    connection_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    user = await ensure_user(db, current_user)
    service = ConnectionService(db)
    result = await service.test_connection(connection_id, user.id)
    if not result["success"] and result["message"] == "Connection not found":
        raise HTTPException(status_code=404, detail="Connection not found")
    return result
