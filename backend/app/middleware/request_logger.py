from __future__ import annotations

import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger()


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # 🔥 CRITICAL FIX: skip preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        start = time.monotonic()

        response = await call_next(request)

        duration = round((time.monotonic() - start) * 1000, 2)

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration,
            user_agent=request.headers.get("user-agent", ""),
        )

        return response