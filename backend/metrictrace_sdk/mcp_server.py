"""Standards-compatible stdio MCP server for real MetricTrace Lite operations."""

from __future__ import annotations

import os
import json
import subprocess
import sys
import time
from pathlib import Path

from metrictrace_sdk.core import validate_metric_sql as validate_sql
from metrictrace_sdk.contracts import ContractError, evaluate_contracts
from metrictrace_sdk.cdc import CdcError, validate_cdc_batch
from metrictrace_sdk.dataset_diff import DatasetDiffError, compare_datasets
from metrictrace_sdk.regression import RegressionError
from metrictrace_sdk.join_audit import JoinAuditError, audit_sql_joins
from metrictrace_sdk.lineage import (
    LineageError,
    compare_sql_lineage,
    inspect_sql_lineage as inspect_static_lineage,
)
from metrictrace_sdk.local_replay import (
    LocalReplayError,
    LocalReplayLimits,
    inspect_datasets,
)
from metrictrace_sdk.reporting import (
    create_report,
    generate_investigation_report as generate_investigation_brief,
    verify_report,
)


def _authorized_roots() -> tuple[str, ...]:
    """MCP callers cannot grant filesystem access by merely naming a path."""
    roots = tuple(
        part for part in os.getenv("METRICTRACE_ALLOWED_DATA_DIRS", "").split(os.pathsep) if part
    )
    if not roots:
        raise PermissionError(
            "Configure METRICTRACE_ALLOWED_DATA_DIRS before local MCP file access."
        )
    return roots


def _limits(timeout_seconds: float, memory_limit: str, threads: int) -> LocalReplayLimits:
    if timeout_seconds <= 0 or threads <= 0:
        raise ValueError("timeout_seconds and threads must be positive.")
    return LocalReplayLimits(
        timeout_seconds=timeout_seconds, memory_limit=memory_limit, threads=threads
    )


def _worker_environment() -> dict[str, str]:
    """Do not pass API tokens or arbitrary inherited variables to SQL execution."""
    names = ("PATH", "SYSTEMROOT", "WINDIR", "HOME", "USERPROFILE", "TMP", "TEMP")
    environment = {name: os.environ[name] for name in names if name in os.environ}
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def _remote_client():
    """Create an authenticated remote client only when explicit config exists."""
    from metrictrace_sdk.client import MetricTraceClient

    base_url = os.getenv("METRICTRACE_REMOTE_API_URL", "").strip()
    token = os.getenv("METRICTRACE_REMOTE_TOKEN", "").strip()
    if not base_url or not token:
        raise PermissionError(
            "Configure METRICTRACE_REMOTE_API_URL and METRICTRACE_REMOTE_TOKEN for remote MCP execution."
        )
    return MetricTraceClient(base_url, token)


def _run_worker(old_datasets, new_datasets, old_sql, new_sql, parameters, limits, roots) -> dict:
    payload = {
        "old_datasets": old_datasets, "new_datasets": new_datasets,
        "old_sql": old_sql, "new_sql": new_sql, "parameters": parameters,
        "allowed_roots": roots, "limits": limits.__dict__,
    }
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "metrictrace_sdk.mcp_worker"], input=json.dumps(payload), text=True,
            capture_output=True, cwd=Path(__file__).resolve().parents[1], env=_worker_environment(),
            timeout=limits.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise LocalReplayError("Metric execution exceeded its wall-clock limit and was terminated.") from exc
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise LocalReplayError("Metric worker ended without a structured result.") from exc
    if completed.returncode or not result.get("ok"):
        raise LocalReplayError(result.get("error", "Metric worker failed."))
    return result["replay"]


def _run_regression_worker(datasets, baseline_sql, candidate_sql, absolute_limit, percent_limit, limits, roots) -> dict:
    payload = {
        "operation": "regression", "datasets": datasets, "baseline_sql": baseline_sql,
        "candidate_sql": candidate_sql, "max_absolute_difference": absolute_limit,
        "max_percent_difference": percent_limit, "allowed_roots": roots,
        "limits": limits.__dict__,
    }
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "metrictrace_sdk.mcp_worker"], input=json.dumps(payload), text=True,
            capture_output=True, cwd=Path(__file__).resolve().parents[1], env=_worker_environment(),
            timeout=max(1, limits.timeout_seconds * 3), check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RegressionError("Regression worker exceeded its wall-clock limit and was terminated.") from exc
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RegressionError("Regression worker ended without a structured result.") from exc
    if completed.returncode or not result.get("ok"):
        raise RegressionError(result.get("error", "Regression worker failed."))
    return result["regression"]


def build_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Install metrictrace-lite[mcp] to run the MetricTrace MCP server."
        ) from exc

    server = FastMCP("MetricTrace Lite")

    @server.tool()
    def validate_metric_sql(sql: str, allowed_tables: list[str] | None = None) -> dict:
        """Validate a read-only SQL metric without accessing data files."""
        try:
            return {
                "ok": True,
                "sql": validate_sql(sql, set(allowed_tables or ["source_data"])),
            }
        except ValueError as exc:
            return {"ok": False, "error": {"code": "invalid_sql", "message": str(exc)}}

    @server.tool()
    def inspect_dataset(datasets: dict[str, str]) -> dict:
        """Inspect authorized CSV/Parquet schemas; dataset records are never returned."""
        try:
            return {
                "ok": True,
                "schema": inspect_datasets(datasets, allowed_roots=_authorized_roots()),
            }
        except (LocalReplayError, PermissionError, ValueError) as exc:
            return {"ok": False, "error": {"code": "dataset_access_denied", "message": str(exc)}}

    @server.tool()
    def compare_local_datasets(
        old_dataset: str,
        new_dataset: str,
        key_columns: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """Compare authorized CSV/Parquet files using validated stable keys or multiset mode."""
        try:
            return {
                "ok": True,
                "comparison": compare_datasets(
                    old_dataset,
                    new_dataset,
                    key_columns=key_columns or [],
                    limit=limit,
                    offset=offset,
                    allowed_roots=_authorized_roots(),
                ),
            }
        except (DatasetDiffError, PermissionError, ValueError) as exc:
            return {"ok": False, "error": {"code": "dataset_comparison_rejected", "message": str(exc)}}

    @server.tool()
    def evaluate_local_contracts(datasets: dict[str, str], contracts: list[dict]) -> dict:
        """Evaluate typed data contracts against authorized local CSV/Parquet files."""
        try:
            report = evaluate_contracts(datasets, contracts, allowed_roots=_authorized_roots())
            return {"ok": report["summary"]["mandatory_passed"], "contracts": report}
        except (ContractError, PermissionError, ValueError) as exc:
            return {"ok": False, "error": {"code": "contract_evaluation_rejected", "message": str(exc)}}

    @server.tool()
    def check_local_sql_regression(
        datasets: dict[str, str],
        baseline_sql: str,
        candidate_sql: str,
        max_absolute_difference: str | None = None,
        max_percent_difference: str | None = None,
    ) -> dict:
        """Run two metric definitions against identical authorized files and apply explicit gates."""
        try:
            report = _run_regression_worker(
                datasets, baseline_sql, candidate_sql, max_absolute_difference,
                max_percent_difference, _limits(20, "256MB", 1), _authorized_roots(),
            )
            return {"ok": report["status"] == "PASS", "regression": report}
        except (RegressionError, PermissionError, ValueError) as exc:
            return {"ok": False, "error": {"code": "regression_check_rejected", "message": str(exc)}}

    @server.tool()
    def audit_local_sql_joins(datasets: dict[str, str], sql: str) -> dict:
        """Profile supported equality joins using authorized local table files."""
        try:
            return {"ok": True, "audit": audit_sql_joins(datasets, sql, allowed_roots=_authorized_roots())}
        except (JoinAuditError, PermissionError, ValueError) as exc:
            return {"ok": False, "error": {"code": "join_audit_rejected", "message": str(exc)}}

    @server.tool()
    def inspect_sql_lineage(sql: str, allowed_tables: list[str]) -> dict:
        """Inspect static dependencies and output columns of authorized read-only metric SQL."""
        try:
            return {"ok": True, "lineage": inspect_static_lineage(sql, allowed_tables)}
        except (LineageError, ValueError) as exc:
            return {"ok": False, "error": {"code": "lineage_inspection_rejected", "message": str(exc)}}

    @server.tool()
    def compare_metric_definitions(
        baseline_sql: str, candidate_sql: str, allowed_tables: list[str]
    ) -> dict:
        """Compare static dependencies and output surface of two authorized metric SQL definitions."""
        try:
            return {
                "ok": True,
                "comparison": compare_sql_lineage(baseline_sql, candidate_sql, allowed_tables),
            }
        except (LineageError, ValueError) as exc:
            return {"ok": False, "error": {"code": "definition_comparison_rejected", "message": str(exc)}}

    @server.tool()
    def inspect_lineage(workspace_id: str, sql: str, allowed_tables: list[str]) -> dict:
        """Inspect tenant-scoped SQL lineage through an authenticated MetricTrace Platform."""
        try:
            from metrictrace_sdk.models import StaticLineageRequest

            result = _remote_client().inspect_static_lineage(
                StaticLineageRequest(workspace_id, sql, allowed_tables)
            )
            return {"ok": True, "lineage": result.lineage}
        except PermissionError as exc:
            return {"ok": False, "error": {"code": "remote_configuration_required", "message": str(exc)}}
        except Exception as exc:
            return {"ok": False, "error": {"code": "remote_lineage_rejected", "message": str(exc)[:512]}}

    @server.tool()
    def run_local_metric_replay(
        old_datasets: dict[str, str],
        new_datasets: dict[str, str],
        old_sql: str,
        new_sql: str,
        parameters: dict[str, object] | None = None,
        timeout_seconds: float = 60,
        memory_limit: str = "256MB",
        threads: int = 1,
    ) -> dict:
        """Execute the four real replay cells within configured authorized directories."""
        try:
            limits = _limits(timeout_seconds, memory_limit, threads)
            started = time.monotonic()
            replay = _run_worker(
                old_datasets,
                new_datasets,
                old_sql,
                new_sql,
                parameters,
                limits,
                _authorized_roots(),
            )
            report = create_report(
                old_datasets,
                new_datasets,
                old_sql,
                new_sql,
                replay,
                limits,
                parameters,
                round((time.monotonic() - started) * 1000),
            )
            return {"ok": True, "report": report}
        except (LocalReplayError, PermissionError, ValueError) as exc:
            return {"ok": False, "error": {"code": "local_replay_rejected", "message": str(exc)}}

    @server.tool()
    def verify_replay_report(report: dict) -> dict:
        """Verify a report digest and numerical reconciliation; it does not re-execute data."""
        return {"ok": True, "verification": verify_report(report)}

    @server.tool()
    def generate_investigation_report(report: dict) -> dict:
        """Create a deterministic, citation-bound brief from one verified local replay report."""
        try:
            return {"ok": True, "investigation": generate_investigation_brief(report)}
        except ValueError as exc:
            return {"ok": False, "error": {"code": "unverified_evidence", "message": str(exc)}}

    @server.tool()
    def validate_cdc_events(events: list[dict], checkpoint_lsn: str | None = None) -> dict:
        """Validate bounded CDC event ordering before a transport advances an LSN checkpoint."""
        try:
            return {"ok": True, "cdc": validate_cdc_batch(events, checkpoint_lsn)}
        except CdcError as exc:
            return {"ok": False, "error": {"code": "cdc_events_rejected", "message": str(exc)}}

    return server


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
