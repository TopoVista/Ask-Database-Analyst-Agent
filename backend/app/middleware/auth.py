from __future__ import annotations

import httpx
import structlog
from fastapi import HTTPException, Request

from app.config import get_settings
from app.schemas.auth import AuthenticatedUser

logger = structlog.get_logger()


def _parse_clerk_payload(payload: dict) -> AuthenticatedUser:
    clerk_id = payload.get("id") or payload.get("sub") or payload.get("user_id") or "unknown"
    email = payload.get("email") or payload.get("email_address")
    if not email and payload.get("email_addresses"):
        email = payload["email_addresses"][0].get("email_address")
    email = email or "unknown@example.com"
    name = payload.get("name") or payload.get("first_name") or payload.get("full_name")
    return AuthenticatedUser(clerk_id=str(clerk_id), email=str(email), name=name)


async def get_current_user(request: Request) -> AuthenticatedUser | None:
    if request.method == "OPTIONS":
        return None

    settings = get_settings()

    if settings.environment == "development":
        return AuthenticatedUser(clerk_id="dev-user", email="dev@example.com", name="Dev User")

    auth_header = request.headers.get("Authorization")

    if not auth_header:
        if settings.auth_bypass:
            return AuthenticatedUser(clerk_id="dev-user", email="dev@example.com", name="Dev User")
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = auth_header.split(" ", 1)[1]

    if settings.auth_bypass or (settings.environment != "production" and not settings.clerk_secret_key):
        return AuthenticatedUser(
            clerk_id=f"local-{abs(hash(token))}",
            email="local@example.com",
            name="Local User",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.clerk.com/v1/tokens/verify",
                headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
                params={"token": token},
            )

        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")

        payload = response.json()

        if isinstance(payload, dict):
            if "user" in payload and isinstance(payload["user"], dict):
                payload = payload["user"]
            return _parse_clerk_payload(payload)

        raise HTTPException(status_code=401, detail="Invalid token")

    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")
