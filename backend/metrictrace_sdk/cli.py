"""Stable JSON-first command-line interface for MetricTrace Lite."""

from __future__ import annotations

import argparse
import json
import time
from contextlib import ExitStack
from decimal import Decimal, InvalidOperation
from importlib.resources import as_file, files
from pathlib import Path

from metrictrace_sdk import __version__
from metrictrace_sdk.core import four_way_attribution, validate_metric_sql
from metrictrace_sdk.contracts import ContractError, evaluate_contracts
from metrictrace_sdk.dataset_diff import DatasetDiffError, compare_datasets, dataset_diff_markdown
from metrictrace_sdk.regression import RegressionError, check_sql_regression
from metrictrace_sdk.join_audit import JoinAuditError, audit_sql_joins
from metrictrace_sdk.local_replay import (
    LocalReplayError,
    LocalReplayLimits,
    inspect_datasets,
    run_local_four_way,
)
from metrictrace_sdk.reporting import create_report, markdown_report, verify_report

EXIT_OK, EXIT_USAGE, EXIT_REMOTE, EXIT_POLICY, EXIT_RESOURCE, EXIT_EXECUTION = range(6)


def _emit(payload: dict, code: int = EXIT_OK, human: bool = False) -> int:
    print(
        payload.get("summary", "")
        if human and payload.get("ok")
        else json.dumps(payload, sort_keys=True, default=str)
    )
    return code


def _read_sql(inline: str | None, file_name: str | None, label: str) -> str:
    if bool(inline) == bool(file_name):
        raise ValueError(f"Specify exactly one of --{label}-sql or --{label}-sql-file.")
    if inline:
        return inline
    try:
        return Path(file_name).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"The {label} SQL file could not be read.") from exc


def _manifest(path: str | None, dataset: str | None, label: str) -> str | dict[str, str]:
    if bool(path) == bool(dataset):
        raise ValueError(f"Specify exactly one of --{label}-dataset or --{label}-manifest.")
    if dataset:
        return dataset
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"The {label} manifest must be a readable JSON object.") from exc
    if not isinstance(raw, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in raw.items()
    ):
        raise ValueError(f"The {label} manifest must map logical table names to file paths.")
    base = Path(path).resolve().parent
    return {
        name: str((base / value).resolve()) if not Path(value).is_absolute() else value
        for name, value in raw.items()
    }


def _parameters(raw: str | None) -> dict[str, object] | None:
    if raw is None:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("--parameters must contain a JSON object.") from exc
    if not isinstance(value, dict):
        raise ValueError("--parameters must contain a JSON object.")
    return value


def _contracts(path: str) -> list[dict]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("--contracts must be a readable JSON contract document.") from exc
    contracts = payload.get("contracts") if isinstance(payload, dict) else payload
    if not isinstance(contracts, list) or not all(isinstance(contract, dict) for contract in contracts):
        raise ValueError("--contracts must be a JSON list or object containing a contracts list.")
    return contracts


def _limits(args) -> LocalReplayLimits:
    if args.timeout_seconds <= 0 or args.threads <= 0:
        raise ValueError("Timeout and thread limits must be positive.")
    return LocalReplayLimits(
        timeout_seconds=args.timeout_seconds, memory_limit=args.memory_limit, threads=args.threads
    )


def _write_output(content: str, destination: str | None) -> None:
    if destination:
        Path(destination).write_text(content, encoding="utf-8")


def _local_replay(args, old_datasets=None, new_datasets=None, old_sql=None, new_sql=None) -> dict:
    limits = _limits(args)
    old_datasets = (
        old_datasets
        if old_datasets is not None
        else _manifest(args.old_manifest, args.old_dataset, "old")
    )
    new_datasets = (
        new_datasets
        if new_datasets is not None
        else _manifest(args.new_manifest, args.new_dataset, "new")
    )
    old_sql = old_sql if old_sql is not None else _read_sql(args.old_sql, args.old_sql_file, "old")
    new_sql = new_sql if new_sql is not None else _read_sql(args.new_sql, args.new_sql_file, "new")
    parameters = _parameters(args.parameters)
    started = time.monotonic()
    replay = run_local_four_way(old_datasets, new_datasets, old_sql, new_sql, limits, parameters)
    return create_report(
        old_datasets,
        new_datasets,
        old_sql,
        new_sql,
        replay,
        limits,
        parameters,
        round((time.monotonic() - started) * 1000),
    )


def _add_local_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--old-dataset")
    parser.add_argument("--new-dataset")
    parser.add_argument("--old-manifest", help="JSON table-to-authorized-file mapping")
    parser.add_argument("--new-manifest", help="JSON table-to-authorized-file mapping")
    parser.add_argument("--old-sql")
    parser.add_argument("--new-sql")
    parser.add_argument("--old-sql-file")
    parser.add_argument("--new-sql-file")
    parser.add_argument("--parameters", help="JSON object of DuckDB named query parameters")
    parser.add_argument("--timeout-seconds", type=float, default=20)
    parser.add_argument("--memory-limit", default="256MB")
    parser.add_argument("--threads", type=int, default=1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="metrictrace", description="MetricTrace Lite deterministic historical replay"
    )
    parser.add_argument("--version", action="version", version=f"metrictrace {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("version", help="Print installed Lite version")
    attribute = sub.add_parser("attribute", help="Compute attribution for four supplied cells")
    for label in ("a", "b", "c", "d"):
        attribute.add_argument(f"--{label}", required=True, help="Decimal metric value")
    validate = sub.add_parser("validate-sql", help="Validate a read-only metric SQL definition")
    validate.add_argument("--sql")
    validate.add_argument("--sql-file")
    validate.add_argument(
        "--tables", default="source_data", help="Comma-separated authorized logical tables"
    )
    inspect = sub.add_parser("inspect", help="Inspect authorized schemas without returning rows")
    inspect.add_argument("--dataset")
    inspect.add_argument("--manifest")
    inspect.add_argument("--memory-limit", default="256MB")
    inspect.add_argument("--timeout-seconds", type=float, default=20)
    inspect.add_argument("--threads", type=int, default=1)
    diff = sub.add_parser("dataset-diff", help="Compare two authorized CSV or Parquet datasets")
    diff.add_argument("--old-dataset", required=True)
    diff.add_argument("--new-dataset", required=True)
    diff.add_argument("--keys", default="", help="Comma-separated stable key columns; omit for multiset comparison")
    diff.add_argument("--limit", type=int, default=100)
    diff.add_argument("--offset", type=int, default=0)
    diff.add_argument("--timeout-seconds", type=float, default=20)
    diff.add_argument("--memory-limit", default="256MB")
    diff.add_argument("--threads", type=int, default=1)
    diff.add_argument("--format", choices=("json", "markdown"), default="json")
    diff.add_argument("--output")
    contracts = sub.add_parser("contracts-evaluate", help="Evaluate declarative contracts against authorized local files")
    contracts.add_argument("--dataset-manifest", required=True, help="JSON mapping of logical table names to CSV/Parquet files")
    contracts.add_argument("--contracts", required=True, help="JSON list or {contracts: [...]} document")
    contracts.add_argument("--timeout-seconds", type=float, default=20)
    contracts.add_argument("--memory-limit", default="256MB")
    contracts.add_argument("--threads", type=int, default=1)
    regression = sub.add_parser("regression-check", help="Run baseline and candidate metric SQL against the same data")
    regression.add_argument("--dataset")
    regression.add_argument("--manifest")
    regression.add_argument("--baseline-sql")
    regression.add_argument("--candidate-sql")
    regression.add_argument("--baseline-sql-file")
    regression.add_argument("--candidate-sql-file")
    regression.add_argument("--parameters")
    regression.add_argument("--max-absolute-difference")
    regression.add_argument("--max-percent-difference")
    regression.add_argument("--timeout-seconds", type=float, default=20)
    regression.add_argument("--memory-limit", default="256MB")
    regression.add_argument("--threads", type=int, default=1)
    join_audit = sub.add_parser("join-audit", help="Profile supported SQL join cardinality against authorized local files")
    join_audit.add_argument("--dataset-manifest", required=True)
    join_audit.add_argument("--sql")
    join_audit.add_argument("--sql-file")
    join_audit.add_argument("--timeout-seconds", type=float, default=20)
    join_audit.add_argument("--memory-limit", default="256MB")
    join_audit.add_argument("--threads", type=int, default=1)
    replay = sub.add_parser("local-replay", help="Run a four-way replay over approved local files")
    _add_local_options(replay)
    replay.add_argument("--format", choices=("json", "markdown"), default="json")
    replay.add_argument("--output")
    replay.add_argument("--human", action="store_true")
    demo = sub.add_parser("demo", help="Run the bundled synthetic revenue replay")
    _add_local_options(demo)
    demo.add_argument("--format", choices=("json", "markdown"), default="json")
    demo.add_argument("--output")
    demo.add_argument("--human", action="store_true")
    verify = sub.add_parser(
        "verify-report", help="Verify report integrity and numerical reconciliation"
    )
    verify.add_argument("--report", required=True)
    remote = sub.add_parser(
        "replay", help="Submit a replay to an authenticated MetricTrace Platform"
    )
    remote.add_argument("--api-url", required=True)
    remote.add_argument("--token", default="")
    for name in (
        "workspace-id",
        "old-version-id",
        "new-version-id",
        "old-definition-id",
        "new-definition-id",
    ):
        remote.add_argument(f"--{name}", required=True)
    status = sub.add_parser("replay-status", help="Read persisted remote replay status")
    status.add_argument("--api-url", required=True)
    status.add_argument("--token", default="")
    status.add_argument("--replay-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "version":
            return _emit({"ok": True, "version": __version__})
        if args.command == "attribute":
            values = (Decimal(getattr(args, label)) for label in ("a", "b", "c", "d"))
            return _emit({"ok": True, "attribution": four_way_attribution(*values)})
        if args.command == "validate-sql":
            return _emit(
                {
                    "ok": True,
                    "sql": validate_metric_sql(
                        _read_sql(args.sql, args.sql_file, "metric"), set(args.tables.split(","))
                    ),
                }
            )
        if args.command == "inspect":
            return _emit(
                {
                    "ok": True,
                    "schema": inspect_datasets(
                        _manifest(args.manifest, args.dataset, "dataset"), _limits(args)
                    ),
                }
            )
        if args.command == "dataset-diff":
            report = compare_datasets(
                args.old_dataset,
                args.new_dataset,
                key_columns=[key.strip() for key in args.keys.split(",") if key.strip()],
                limit=args.limit,
                offset=args.offset,
                limits=_limits(args),
            )
            rendered = dataset_diff_markdown(report) if args.format == "markdown" else json.dumps(report, sort_keys=True, indent=2, default=str)
            _write_output(rendered, args.output)
            return _emit({"ok": True, "comparison": report} if not args.output else {"ok": True, "output": args.output, "fingerprint": report["fingerprint"]})
        if args.command == "contracts-evaluate":
            report = evaluate_contracts(
                _manifest(args.dataset_manifest, None, "dataset"),
                _contracts(args.contracts),
                limits=_limits(args),
            )
            return _emit({"ok": report["summary"]["mandatory_passed"], "contracts": report}, EXIT_OK if report["summary"]["mandatory_passed"] else EXIT_EXECUTION)
        if args.command == "regression-check":
            report = check_sql_regression(
                _manifest(args.manifest, args.dataset, "dataset"),
                _read_sql(args.baseline_sql, args.baseline_sql_file, "baseline"),
                _read_sql(args.candidate_sql, args.candidate_sql_file, "candidate"),
                max_absolute_difference=args.max_absolute_difference,
                max_percent_difference=args.max_percent_difference,
                parameters=_parameters(args.parameters),
                limits=_limits(args),
            )
            return _emit({"ok": report["status"] == "PASS", "regression": report}, EXIT_OK if report["status"] == "PASS" else EXIT_POLICY)
        if args.command == "join-audit":
            report = audit_sql_joins(
                _manifest(args.dataset_manifest, None, "dataset"),
                _read_sql(args.sql, args.sql_file, "join"),
                limits=_limits(args),
            )
            return _emit({"ok": True, "audit": report})
        if args.command == "verify-report":
            verdict = verify_report(json.loads(Path(args.report).read_text(encoding="utf-8")))
            return _emit(
                {"ok": verdict["valid"], "verification": verdict},
                EXIT_OK if verdict["valid"] else EXIT_EXECUTION,
            )
        if args.command == "demo":
            with ExitStack() as stack:
                root = files("metrictrace_sdk.examples")
                old_data = stack.enter_context(as_file(root / "local-old.csv"))
                new_data = stack.enter_context(as_file(root / "local-new.csv"))
                report = _local_replay(
                    args,
                    str(old_data),
                    str(new_data),
                    (root / "old.sql").read_text(),
                    (root / "new.sql").read_text(),
                )
        elif args.command == "local-replay":
            report = _local_replay(args)
        else:
            from metrictrace_sdk.client import MetricTraceClient
            from metrictrace_sdk.models import FourWayReplayRequest

            client = MetricTraceClient(args.api_url, args.token)
            if args.command == "replay-status":
                return _emit({"ok": True, "replay": client.get_replay(args.replay_id)})
            result = client.run_four_way_replay(
                FourWayReplayRequest(
                    args.workspace_id,
                    args.old_version_id,
                    args.new_version_id,
                    args.old_definition_id,
                    args.new_definition_id,
                )
            )
            return _emit(
                {
                    "ok": True,
                    "replay_id": result.replay_id,
                    "status": result.status,
                    "attribution": result.attribution,
                }
            )
        rendered = (
            markdown_report(report)
            if args.format == "markdown"
            else json.dumps(report, sort_keys=True, indent=2)
        )
        _write_output(rendered, args.output)
        summary = f"Replay complete: total change {report['replay']['attribution']['total_change']}; reconciles={report['replay']['attribution']['reconciles']}"
        return _emit(
            {"ok": True, "output": args.output, "summary": summary}
            if args.output
            else {"ok": True, "report": report, "summary": summary},
            human=args.human,
        )
    except InvalidOperation:
        return _emit(
            {
                "ok": False,
                "error": {
                    "code": "invalid_decimal",
                    "message": "Metric values must be finite decimal values.",
                },
            },
            EXIT_USAGE,
        )
    except (ValueError, LocalReplayError, DatasetDiffError, ContractError, RegressionError, JoinAuditError) as exc:
        message = str(exc)
        code = EXIT_RESOURCE if "limit" in message or "terminated" in message else EXIT_POLICY
        return _emit(
            {"ok": False, "error": {"code": "local_replay_error", "message": message}}, code
        )
    except Exception as exc:
        return _emit(
            {"ok": False, "error": {"code": "execution_error", "message": str(exc)[:512]}},
            EXIT_EXECUTION,
        )


if __name__ == "__main__":
    raise SystemExit(main())
