"""Dedicated HTTP service for resource-isolated specialist execution."""

from __future__ import annotations

import inspect
import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.workers.common import enforce_specialist_limits, require_worker_token

app = FastAPI(title="Decision Intelligence Specialist Worker", version="1.0.0", docs_url=None)


@app.middleware("http")
async def reject_oversized_bodies(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > get_settings().worker_max_request_bytes:
                return JSONResponse(status_code=413, content={"detail": "Worker request exceeds its memory-safe limit."})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."})
    return await call_next(request)


class Invocation(BaseModel):
    skill: str = Field(min_length=1, max_length=100)
    params: dict[str, Any] = Field(default_factory=dict)


def _allowed_specialists() -> set[str]:
    return {value.strip() for value in os.getenv("WORKER_SPECIALISTS", "").split(",") if value.strip()}


def _skills(instance: Any) -> dict[str, Any]:
    return {
        getattr(method, "__skill_name__"): method
        for _, method in inspect.getmembers(instance, predicate=callable)
        if getattr(method, "__skill_name__", None)
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "specialists": sorted(_allowed_specialists())}


@app.post("/v1/specialists/{specialist_id}/invoke", dependencies=[Depends(require_worker_token)])
async def invoke(specialist_id: str, body: Invocation) -> dict[str, Any]:
    allowed = _allowed_specialists()
    if specialist_id not in allowed:
        raise HTTPException(status_code=404, detail="This specialist is not assigned to this worker.")
    enforce_specialist_limits(body.params)

    from app.specialists import get_specialist_class

    specialist_class = get_specialist_class(specialist_id)
    if specialist_class is None:
        raise HTTPException(status_code=501, detail="This specialist requires pipeline orchestration.")
    method = _skills(specialist_class()).get(body.skill)
    if method is None:
        raise HTTPException(status_code=404, detail="Unknown specialist skill.")
    try:
        inspect.signature(method).bind(**body.params)
        result = await method(**body.params)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid skill parameters: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Specialist execution failed.") from exc
    return {"specialist_id": specialist_id, "skill": body.skill, "result": result}
