"""Small authenticated clients for optional private Render workers."""

from __future__ import annotations

import base64
from typing import Any

import httpx

from app.config import get_settings


class WorkerUnavailableError(RuntimeError):
    """Raised when an enabled worker cannot safely complete a request."""


def specialist_worker_url(specialist_id: str) -> str:
    """Resolve ``SPECIALIST_WORKER_URLS`` without exposing arbitrary URLs."""
    mappings = get_settings().specialist_worker_urls.split(",")
    for mapping in mappings:
        key, separator, value = mapping.partition("=")
        if separator and key.strip() == specialist_id:
            return value.strip().rstrip("/")
    return ""


class _WorkerClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.settings = get_settings()

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.worker_shared_token:
            raise WorkerUnavailableError("Worker routing is enabled but WORKER_SHARED_TOKEN is not configured.")
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.worker_timeout_seconds),
                headers={"X-Worker-Token": self.settings.worker_shared_token},
            ) as client:
                response = await client.post(f"{self.base_url}{path}", json=payload)
        except httpx.HTTPError as exc:
            raise WorkerUnavailableError("The worker service is unavailable. Please retry shortly.") from exc
        if response.status_code >= 400:
            raise WorkerUnavailableError("The worker could not process this request safely.")
        try:
            result = response.json()
        except ValueError as exc:
            raise WorkerUnavailableError("The worker returned an invalid response.") from exc
        if not isinstance(result, dict):
            raise WorkerUnavailableError("The worker returned an invalid response.")
        return result


class SpecialistWorkerClient(_WorkerClient):
    async def invoke(self, specialist_id: str, skill: str, params: dict[str, Any]) -> Any:
        result = await self._post(
            f"/v1/specialists/{specialist_id}/invoke",
            {"skill": skill, "params": params},
        )
        return result.get("result")


class RAGWorkerClient(_WorkerClient):
    async def ingest(self, content: bytes, source: str, user_id: str) -> dict[str, Any]:
        if len(content) > self.settings.worker_max_request_bytes:
            raise WorkerUnavailableError(
                f"Document exceeds the {self.settings.worker_max_request_bytes} byte RAG worker limit."
            )
        return await self._post(
            "/v1/documents/ingest",
            {"content_base64": base64.b64encode(content).decode("ascii"), "source": source, "user_id": user_id},
        )

    async def search(self, query: str, user_id: str, limit: int, source: str | None) -> dict[str, Any]:
        return await self._post(
            "/v1/documents/search",
            {"query": query, "user_id": user_id, "limit": limit, "source": source},
        )

    async def delete(self, source: str, user_id: str) -> dict[str, Any]:
        return await self._post("/v1/documents/delete", {"source": source, "user_id": user_id})
