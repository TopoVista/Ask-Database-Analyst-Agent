from __future__ import annotations

import os
import sys
import json
from pathlib import Path

import pytest

mcp = pytest.importorskip("mcp")
from mcp import ClientSession  # noqa: E402
from mcp.client.stdio import StdioServerParameters, stdio_client  # noqa: E402


def _content(result) -> str:
    return "\n".join(item.text for item in result.content if hasattr(item, "text"))


@pytest.mark.asyncio
async def test_mcp_stdio_protocol_executes_and_rejects_unapproved_paths(tmp_path):
    data = tmp_path / "data.csv"
    data.write_text("amount\n10\n", encoding="utf-8")
    changed = tmp_path / "changed.csv"
    changed.write_text("amount\n12\n", encoding="utf-8")
    env = os.environ.copy()
    env["METRICTRACE_ALLOWED_DATA_DIRS"] = str(tmp_path)
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "metrictrace_sdk.mcp_server"],
        cwd=Path(__file__).parents[2],
        env=env,
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            assert initialized.serverInfo.name == "MetricTrace Lite"
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "compare_local_datasets",
                "compare_metric_definitions",
                "evaluate_local_contracts",
                "check_local_sql_regression",
                "audit_local_sql_joins",
                "inspect_dataset",
                "inspect_lineage",
                "inspect_sql_lineage",
                "run_local_metric_replay",
                "validate_metric_sql",
                "verify_replay_report",
            }
            valid_sql = await session.call_tool(
                "validate_metric_sql", {"sql": "SELECT SUM(amount) FROM source_data"}
            )
            assert '"ok":true' in _content(valid_sql).replace(" ", "")
            invalid_sql = await session.call_tool(
                "validate_metric_sql", {"sql": "SELECT * FROM read_csv_auto('secret.csv')"}
            )
            assert "invalid_sql" in _content(invalid_sql)
            lineage = await session.call_tool(
                "inspect_sql_lineage",
                {"sql": "SELECT SUM(amount) AS total FROM source_data", "allowed_tables": ["source_data"]},
            )
            assert json.loads(_content(lineage))["lineage"]["source_tables"] == ["source_data"]
            definition_comparison = await session.call_tool(
                "compare_metric_definitions",
                {
                    "baseline_sql": "SELECT amount FROM source_data",
                    "candidate_sql": "SELECT amount, 1 AS revision FROM source_data",
                    "allowed_tables": ["source_data"],
                },
            )
            assert json.loads(_content(definition_comparison))["comparison"]["change"]["output_columns"]["added"] == ["revision"]
            remote_lineage = await session.call_tool(
                "inspect_lineage",
                {"workspace_id": "workspace-id", "sql": "SELECT * FROM source_data", "allowed_tables": ["source_data"]},
            )
            assert "remote_configuration_required" in _content(remote_lineage)
            replay = await session.call_tool(
                "run_local_metric_replay",
                {
                    "old_datasets": {"source_data": str(data)},
                    "new_datasets": {"source_data": str(data)},
                    "old_sql": "SELECT SUM(amount) FROM source_data",
                    "new_sql": "SELECT SUM(amount) FROM source_data",
                },
            )
            assert '"total_change":"0"' in _content(replay).replace(" ", "")
            report = json.loads(_content(replay))["report"]
            verified = await session.call_tool("verify_replay_report", {"report": report})
            assert '"valid":true' in _content(verified).replace(" ", "")
            rejected = await session.call_tool(
                "inspect_dataset", {"datasets": {"source_data": str(tmp_path.parent / "not-approved.csv")}}
            )
            assert "dataset_access_denied" in _content(rejected)
            comparison = await session.call_tool(
                "compare_local_datasets",
                {"old_dataset": str(data), "new_dataset": str(changed)},
            )
            assert '"mode":"multiset"' in _content(comparison).replace(" ", "")
            comparison_rejected = await session.call_tool(
                "compare_local_datasets",
                {"old_dataset": str(data), "new_dataset": str(tmp_path.parent / "not-approved.csv")},
            )
            assert "dataset_comparison_rejected" in _content(comparison_rejected)
            contract_result = await session.call_tool(
                "evaluate_local_contracts",
                {"datasets": {"source_data": str(data)}, "contracts": [{"id": "nonnull", "type": "non_null", "table": "source_data", "column": "amount"}]},
            )
            assert '"mandatory_passed":true' in _content(contract_result).replace(" ", "")
            regression = await session.call_tool(
                "check_local_sql_regression",
                {"datasets": {"source_data": str(data)}, "baseline_sql": "SELECT SUM(amount) FROM source_data", "candidate_sql": "SELECT SUM(amount) FROM source_data", "max_absolute_difference": "0"},
            )
            assert '"status":"PASS"' in _content(regression).replace(" ", "")
            audit = await session.call_tool(
                "audit_local_sql_joins",
                {"datasets": {"source_data": str(data)}, "sql": "SELECT SUM(amount) FROM source_data"},
            )
            assert '"supported":false' in _content(audit).replace(" ", "")
            timed_out = await session.call_tool(
                "run_local_metric_replay",
                {
                    "old_datasets": {"source_data": str(data)},
                    "new_datasets": {"source_data": str(data)},
                    "old_sql": "SELECT SUM(amount) FROM source_data",
                    "new_sql": "SELECT SUM(amount) FROM source_data",
                    "timeout_seconds": 0.01,
                },
            )
            assert "wall-clock" in _content(timed_out)
