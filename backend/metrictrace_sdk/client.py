from __future__ import annotations

from typing import Any

from metrictrace_sdk.models import FourWayReplayRequest, ReplayResult


class RemoteMetricTraceError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code, self.code = status_code, code
        super().__init__(message)


class MetricTraceClient:
    def __init__(self, base_url: str, token: str = "", timeout_seconds: float = 30):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _request(self, method: str, path: str, json: dict | None = None) -> dict[str, Any]:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("Install metrictrace-lite[remote] for remote API support.") from exc
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.request(method, f"{self.base_url}{path}", headers=self._headers(), json=json)
        if response.is_error:
            try:
                detail = response.json().get("detail", "Remote MetricTrace request failed")
            except ValueError:
                detail = "Remote MetricTrace request failed"
            raise RemoteMetricTraceError(response.status_code, "remote_error", str(detail))
        return response.json()

    def run_four_way_replay(self, request: FourWayReplayRequest) -> ReplayResult:
        data = self._request("POST", "/api/v1/metrictrace/replays", request.__dict__)
        return ReplayResult(replay_id=data["replay_id"], status=data["status"], attribution=data.get("attribution"))

    def get_replay(self, replay_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/metrictrace/replays/{replay_id}")

    def run_canonical_demo(self) -> dict[str, Any]:
        return self._request("POST", "/api/v1/metrictrace/demo")
