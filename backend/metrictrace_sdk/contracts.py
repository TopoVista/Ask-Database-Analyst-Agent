"""Typed, declarative data-contract evaluation over authorized local files."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from metrictrace_sdk.core import validate_metric_sql
from metrictrace_sdk.local_replay import LocalReplayError, LocalReplayLimits, normalize_datasets

PASS, FAIL, ERROR, NOT_EVALUATED = "PASS", "FAIL", "ERROR", "NOT_EVALUATED"


class ContractError(RuntimeError):
    """Stable contract configuration or evaluation error."""


def _quote(identifier: str) -> str:
    if not isinstance(identifier, str) or not identifier:
        raise ContractError("Table and column names must be non-empty strings.")
    return '"' + identifier.replace('"', '""') + '"'


def _reader(path: Path) -> str:
    escaped = path.as_posix().replace("'", "''")
    return f"{'read_parquet' if path.suffix.lower() == '.parquet' else 'read_csv_auto'}('{escaped}')"


def _decimal(value: Any, field: str) -> Decimal:
    try:
        converted = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ContractError(f"{field} must be a finite decimal value.") from exc
    if not converted.is_finite():
        raise ContractError(f"{field} must be a finite decimal value.")
    return converted


def _schema(connection: Any, table: str) -> dict[str, str]:
    return {row[0]: str(row[1]).upper() for row in connection.execute(f"DESCRIBE {_quote(table)}").fetchall()}


def _scalar(connection: Any, sql: str, tables: set[str]) -> Any:
    validated = validate_metric_sql(sql, tables)
    row = connection.execute(validated).fetchone()
    if row is None or len(row) != 1:
        raise ContractError("A SQL assertion must return exactly one scalar value.")
    return row[0]


def _outcome(contract: dict[str, Any], status: str, evidence: dict[str, Any], message: str = "") -> dict[str, Any]:
    return {
        "id": contract["id"],
        "type": contract["type"],
        "severity": contract.get("severity", "error"),
        "status": status,
        "message": message,
        "evidence": evidence,
    }


def _contract_id(contract: dict[str, Any], index: int) -> dict[str, Any]:
    normalized = dict(contract)
    identifier = normalized.get("id", f"contract-{index + 1}")
    if not isinstance(identifier, str) or not identifier:
        raise ContractError("Every contract id must be a non-empty string.")
    normalized["id"] = identifier
    if normalized.get("severity", "error") not in {"error", "warning"}:
        raise ContractError(f"{identifier}: severity must be 'error' or 'warning'.")
    return normalized


def _evaluate(connection: Any, contract: dict[str, Any], tables: set[str], schemas: dict[str, dict[str, str]]) -> dict[str, Any]:
    kind = contract.get("type")
    table = contract.get("table")
    if kind in {"required_columns", "schema_type", "non_null", "minimum", "maximum", "non_negative", "primary_key_unique", "freshness", "referential_integrity"}:
        if table not in tables:
            return _outcome(contract, NOT_EVALUATED, {}, f"Authorized table {table!r} is unavailable.")
    if kind == "required_columns":
        columns = contract.get("columns")
        if not isinstance(columns, list) or not columns:
            raise ContractError("required_columns needs a non-empty columns list.")
        missing = sorted(set(columns) - set(schemas[table]))
        return _outcome(contract, PASS if not missing else FAIL, {"missing_columns": missing, "available_columns": sorted(schemas[table])})
    if kind == "schema_type":
        column, expected = contract.get("column"), contract.get("expected_type")
        actual = schemas[table].get(column)
        if actual is None:
            return _outcome(contract, NOT_EVALUATED, {"column": column}, "Contract column is unavailable.")
        return _outcome(contract, PASS if actual == str(expected).upper() else FAIL, {"column": column, "expected_type": str(expected).upper(), "actual_type": actual})
    if kind in {"non_null", "minimum", "maximum", "non_negative"}:
        column = contract.get("column")
        if column not in schemas[table]:
            return _outcome(contract, NOT_EVALUATED, {"column": column}, "Contract column is unavailable.")
        quoted = _quote(column)
        if kind == "non_null":
            violations = connection.execute(f"SELECT COUNT(*) FROM {_quote(table)} WHERE {quoted} IS NULL").fetchone()[0]
            return _outcome(contract, PASS if not violations else FAIL, {"null_rows": int(violations)})
        threshold = Decimal("0") if kind == "non_negative" else _decimal(contract.get("value"), "value")
        operator = ">=" if kind in {"minimum", "non_negative"} else "<="
        violations = connection.execute(f"SELECT COUNT(*) FROM {_quote(table)} WHERE {quoted} IS NOT NULL AND {quoted} {('<' if operator == '>=' else '>')} ?", [threshold]).fetchone()[0]
        return _outcome(contract, PASS if not violations else FAIL, {"column": column, "operator": operator, "threshold": str(threshold), "violating_rows": int(violations)})
    if kind == "primary_key_unique":
        columns = contract.get("columns")
        if not isinstance(columns, list) or not columns or any(column not in schemas[table] for column in columns):
            return _outcome(contract, NOT_EVALUATED, {"columns": columns}, "Primary-key columns are unavailable.")
        quoted = ", ".join(_quote(column) for column in columns)
        nulls = " OR ".join(f"{_quote(column)} IS NULL" for column in columns)
        duplicate_groups = connection.execute(f"SELECT COUNT(*) FROM (SELECT {quoted} FROM {_quote(table)} GROUP BY {quoted} HAVING COUNT(*) > 1)").fetchone()[0]
        null_rows = connection.execute(f"SELECT COUNT(*) FROM {_quote(table)} WHERE {nulls}").fetchone()[0]
        return _outcome(contract, PASS if not duplicate_groups and not null_rows else FAIL, {"duplicate_key_groups": int(duplicate_groups), "null_key_rows": int(null_rows)})
    if kind in {"absolute_change", "percentage_change"}:
        actual, baseline = _decimal(contract.get("actual"), "actual"), _decimal(contract.get("baseline"), "baseline")
        if kind == "absolute_change":
            maximum = _decimal(contract.get("max_change"), "max_change")
            change = abs(actual - baseline)
        else:
            if baseline == 0:
                return _outcome(contract, ERROR, {"actual": str(actual), "baseline": str(baseline)}, "Percentage change is undefined for a zero baseline.")
            maximum = _decimal(contract.get("max_percent"), "max_percent")
            change = abs((actual - baseline) / baseline * Decimal("100"))
        return _outcome(contract, PASS if change <= maximum else FAIL, {"actual": str(actual), "baseline": str(baseline), "change": str(change), "maximum": str(maximum)})
    if kind == "referential_integrity":
        column, ref_table, ref_column = contract.get("column"), contract.get("reference_table"), contract.get("reference_column")
        if column not in schemas[table] or ref_table not in tables or ref_column not in schemas.get(ref_table, {}):
            return _outcome(contract, NOT_EVALUATED, {}, "Referential-integrity columns or table are unavailable.")
        violations = connection.execute(
            f"SELECT COUNT(*) FROM {_quote(table)} child LEFT JOIN {_quote(ref_table)} parent ON child.{_quote(column)} = parent.{_quote(ref_column)} WHERE child.{_quote(column)} IS NOT NULL AND parent.{_quote(ref_column)} IS NULL"
        ).fetchone()[0]
        return _outcome(contract, PASS if not violations else FAIL, {"orphan_rows": int(violations)})
    if kind == "freshness":
        column = contract.get("column")
        if column not in schemas[table]:
            return _outcome(contract, NOT_EVALUATED, {"column": column}, "Freshness column is unavailable.")
        maximum_age = _decimal(contract.get("max_age_seconds"), "max_age_seconds")
        newest = connection.execute(f"SELECT MAX({_quote(column)}) FROM {_quote(table)}").fetchone()[0]
        if newest is None:
            return _outcome(contract, FAIL, {"newest": None}, "No timestamp value is available.")
        if not isinstance(newest, datetime):
            return _outcome(contract, ERROR, {"newest": str(newest)}, "Freshness column did not evaluate to a timestamp.")
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=timezone.utc)
        age = Decimal(str((datetime.now(timezone.utc) - newest.astimezone(timezone.utc)).total_seconds()))
        return _outcome(contract, PASS if age <= maximum_age else FAIL, {"newest": newest.isoformat(), "age_seconds": str(age), "max_age_seconds": str(maximum_age)})
    if kind == "sql_assertion":
        value = _scalar(connection, contract.get("sql", ""), tables)
        passed = value is True or (isinstance(value, (int, float, Decimal)) and value != 0)
        return _outcome(contract, PASS if passed else FAIL, {"result": str(value)})
    if kind == "cross_metric_reconciliation":
        left = _decimal(_scalar(connection, contract.get("left_sql", ""), tables), "left_sql result")
        right = _decimal(_scalar(connection, contract.get("right_sql", ""), tables), "right_sql result")
        tolerance = _decimal(contract.get("tolerance", "0"), "tolerance")
        difference = abs(left - right)
        return _outcome(contract, PASS if difference <= tolerance else FAIL, {"left": str(left), "right": str(right), "difference": str(difference), "tolerance": str(tolerance)})
    raise ContractError(f"Unsupported contract type {kind!r}.")


def evaluate_contracts(
    datasets: dict[str, str],
    contracts: Iterable[dict[str, Any]],
    *,
    limits: LocalReplayLimits = LocalReplayLimits(),
    allowed_roots: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Evaluate versioned JSON/YAML-decoded contract objects against local files."""
    try:
        paths = normalize_datasets(datasets, limits, allowed_roots)
    except LocalReplayError as exc:
        raise ContractError(str(exc)) from exc
    normalized = [_contract_id(contract, index) for index, contract in enumerate(contracts)]
    if len({contract["id"] for contract in normalized}) != len(normalized):
        raise ContractError("Contract IDs must be unique.")
    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover
        raise ContractError("Contract evaluation requires duckdb.") from exc
    connection = duckdb.connect(":memory:")
    try:
        connection.execute(f"SET memory_limit = '{limits.memory_limit}'")
        connection.execute(f"SET threads = {max(1, min(limits.threads, 32))}")
        for table, path in paths.items():
            connection.execute(f"CREATE VIEW {_quote(table)} AS SELECT * FROM {_reader(path)}")
        schemas = {table: _schema(connection, table) for table in paths}
        results = []
        for contract in normalized:
            try:
                results.append(_evaluate(connection, contract, set(paths), schemas))
            except ContractError as exc:
                results.append(_outcome(contract, ERROR, {}, str(exc)))
            except Exception as exc:  # Structured error; do not hide failed mandatory validation.
                results.append(_outcome(contract, ERROR, {}, str(exc)[:512]))
        mandatory = [result for result in results if result["severity"] == "error"]
        return {
            "format_version": 1,
            "outcomes": results,
            "summary": {
                status: sum(1 for result in results if result["status"] == status)
                for status in (PASS, FAIL, ERROR, NOT_EVALUATED)
            } | {"mandatory_passed": all(result["status"] == PASS for result in mandatory)},
            "fingerprint": hashlib.sha256(json.dumps({"datasets": {name: str(path) for name, path in paths.items()}, "contracts": normalized}, sort_keys=True, default=str).encode()).hexdigest(),
        }
    finally:
        connection.close()
