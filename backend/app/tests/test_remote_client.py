from __future__ import annotations

from metrictrace_sdk.client import MetricTraceClient
from metrictrace_sdk.cli import main
from metrictrace_sdk.models import StaticLineageRequest


def test_public_sdk_exports_static_lineage_types():
    from metrictrace_sdk import StaticLineageRequest as PublicRequest
    from metrictrace_sdk import StaticLineageResult

    assert PublicRequest is StaticLineageRequest
    assert StaticLineageResult(lineage={"source_tables": []}).lineage == {"source_tables": []}


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


def test_remote_lineage_cli_uses_typed_client(monkeypatch, capsys):
    class FakeClient:
        def __init__(self, base_url, token):
            assert (base_url, token) == ("https://metrictrace.example", "token")

        def inspect_static_lineage(self, request):
            assert request.workspace_id == "workspace-id"
            assert request.tables == ["orders"]
            return type("Result", (), {"lineage": {"source_tables": ["orders"]}})()

    monkeypatch.setattr("metrictrace_sdk.client.MetricTraceClient", FakeClient)
    assert main([
        "remote-lineage-inspect", "--api-url", "https://metrictrace.example", "--token", "token",
        "--workspace-id", "workspace-id", "--sql", "SELECT * FROM orders", "--tables", "orders",
    ]) == 0
    assert '"source_tables": ["orders"]' in capsys.readouterr().out
