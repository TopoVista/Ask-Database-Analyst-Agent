from __future__ import annotations

from metrictrace_sdk.client import MetricTraceClient
from metrictrace_sdk.models import StaticLineageRequest


def test_remote_client_sends_typed_static_lineage_request(monkeypatch):
    client = MetricTraceClient("https://metrictrace.example", "token")
    captured = {}

    def request(method, path, json=None):
        captured.update(method=method, path=path, json=json)
        return {"lineage": {"source_tables": ["orders"]}}

    monkeypatch.setattr(client, "_request", request)
    result = client.inspect_static_lineage(
        StaticLineageRequest("workspace-id", "SELECT * FROM orders", ["orders"])
    )

    assert result.lineage["source_tables"] == ["orders"]
    assert captured == {
        "method": "POST",
        "path": "/api/v1/metrictrace/lineage/inspect",
        "json": {"workspace_id": "workspace-id", "sql": "SELECT * FROM orders", "tables": ["orders"]},
    }
