from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import get_settings

settings = get_settings()
_COUNTS: dict[str, int] = defaultdict(int)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # 🔥 CRITICAL FIX: allow preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # optional skip paths
        if request.url.path in {"/health", "/docs", "/openapi.json"}:
            return await call_next(request)

        user_id = request.headers.get("x-user-id") or request.client.host
        minute = int(time.time() // 60)
        key = f"{user_id}:{minute}"

        _COUNTS[key] += 1

        if _COUNTS[key] > settings.rate_limit_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Max {settings.rate_limit_requests} requests per minute."},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)