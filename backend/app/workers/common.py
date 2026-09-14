"""Shared authentication and request limits for private worker services."""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import Header, HTTPException

from app.config import get_settings


def require_worker_token(x_worker_token: str | None = Header(default=None)) -> None:
    token = get_settings().worker_shared_token
    if not token or not x_worker_token or not secrets.compare_digest(token, x_worker_token):
        raise HTTPException(status_code=401, detail="Invalid worker token.")


def enforce_specialist_limits(params: dict[str, Any]) -> None:
    settings = get_settings()
    for key in ("data", "rows", "values"):
        if isinstance(params.get(key), list) and len(params[key]) > settings.max_specialist_rows:
            raise HTTPException(status_code=422, detail=f"'{key}' exceeds the worker row limit.")
    if isinstance(params.get("columns"), list) and len(params["columns"]) > settings.max_specialist_columns:
        raise HTTPException(status_code=422, detail="'columns' exceeds the worker column limit.")
