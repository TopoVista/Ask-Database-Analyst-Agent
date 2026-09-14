"""Dedicated HTTP service for bounded document ingestion and retrieval."""

from __future__ import annotations

import base64
import binascii
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.rag.retriever import RAGRetriever
from app.rag.vector_store import get_default_store
from app.workers.common import require_worker_token

app = FastAPI(title="Decision Intelligence RAG Worker", version="1.0.0", docs_url=None)


@app.middleware("http")
async def reject_oversized_bodies(request: Request, call_next):
    """Reject known oversized base64 payloads before JSON parsing allocates RAM."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > get_settings().worker_max_request_bytes * 2:
                return JSONResponse(status_code=413, content={"detail": "Worker request exceeds its memory-safe limit."})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."})
    return await call_next(request)


class IngestRequest(BaseModel):
    content_base64: str = Field(min_length=1)
    source: str = Field(min_length=1, max_length=512)
    user_id: str = Field(min_length=1, max_length=128)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1_000)
    user_id: str = Field(min_length=1, max_length=128)
    limit: int = Field(default=5, ge=1, le=20)
    source: str | None = Field(default=None, max_length=512)


class DeleteRequest(BaseModel):
    source: str = Field(min_length=1, max_length=512)
    user_id: str = Field(min_length=1, max_length=128)


def _retriever() -> RAGRetriever:
    return RAGRetriever(vector_store=get_default_store())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "store_backend": get_settings().rag_store_backend}


@app.post("/v1/documents/ingest", dependencies=[Depends(require_worker_token)])
async def ingest(body: IngestRequest) -> dict[str, Any]:
    try:
        content = base64.b64decode(body.content_base64.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise HTTPException(status_code=422, detail="Invalid document payload.") from exc
    if len(content) > get_settings().worker_max_request_bytes:
        raise HTTPException(status_code=413, detail="Document exceeds the RAG worker size limit.")
    try:
        return await _retriever().ingest_document(content, body.source, body.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except MemoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/v1/documents/search", dependencies=[Depends(require_worker_token)])
async def search(body: SearchRequest) -> dict[str, Any]:
    results = await _retriever().retrieve(body.query, body.user_id, limit=body.limit, source=body.source)
    return {"query": body.query, "results": [item.to_dict() for item in results], "count": len(results)}


@app.post("/v1/documents/delete", dependencies=[Depends(require_worker_token)])
async def delete(body: DeleteRequest) -> dict[str, Any]:
    deleted = await _retriever().delete_document(body.source, body.user_id)
    return {"source": body.source, "chunks_deleted": deleted}
