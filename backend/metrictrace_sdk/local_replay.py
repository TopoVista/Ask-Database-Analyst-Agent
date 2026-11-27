"""Isolated, local DuckDB execution used by MetricTrace Lite and Platform."""

from __future__ import annotations

import multiprocessing as mp
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from queue import Empty
from typing import Mapping

from metrictrace_sdk.core import four_way_attribution, validate_metric_sql

_TABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SUPPORTED_SUFFIXES = {".csv", ".parquet"}


@dataclass(frozen=True)
class LocalReplayLimits:
    """Best-effort limits; DuckDB memory limits are not an OS sandbox."""

    timeout_seconds: float = 20
    memory_limit: str = "256MB"
    threads: int = 1
    max_result_bytes: int = 64 * 1024
    max_input_bytes: int = 512 * 1024 * 1024


class LocalReplayError(RuntimeError):
    """A safe, stable error from local replay."""


def _trusted_path(
    value: str, limits: LocalReplayLimits, allowed_roots: tuple[str, ...] = ()
) -> Path:
    try:
        resolved = Path(value).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise LocalReplayError("An authorized dataset file could not be opened.") from exc
    if resolved.suffix.lower() not in _SUPPORTED_SUFFIXES:
        raise LocalReplayError("Only CSV and Parquet inputs are supported.")
    if not resolved.is_file() or resolved.stat().st_size > limits.max_input_bytes:
        raise LocalReplayError("Dataset is unavailable or exceeds the configured input limit.")
    if allowed_roots:
        roots = tuple(Path(root).resolve() for root in allowed_roots)
        if not any(resolved.is_relative_to(root) for root in roots):
            raise LocalReplayError("Dataset path is outside the authorized directories.")
    return resolved


def normalize_datasets(
    datasets: str | Mapping[str, str],
    limits: LocalReplayLimits,
    allowed_roots: tuple[str, ...] = (),
) -> dict[str, Path]:
    """Validate explicitly authorized logical table names and local files."""
    items = {"source_data": datasets}.items() if isinstance(datasets, str) else datasets.items()
    normalized: dict[str, Path] = {}
    for name, value in items:
        if not isinstance(name, str) or not _TABLE_NAME.fullmatch(name):
            raise LocalReplayError("Logical table names must be valid SQL identifiers.")
        if name.lower() in {"duckdb_tables", "information_schema", "pg_catalog"}:
            raise LocalReplayError("Reserved logical table name is not allowed.")
        if not isinstance(value, str):
            raise LocalReplayError("Each logical table must name one local file.")
        normalized[name.lower()] = _trusted_path(value, limits, allowed_roots)
    if not normalized:
        raise LocalReplayError("At least one authorized dataset is required.")
    return normalized


def _child(
    datasets: dict[str, str],
    sql: str,
    parameters: dict[str, object] | None,
    limits: LocalReplayLimits,
    output,
) -> None:
    try:
        output.put({"ok": True, "value": _execute_scalar(datasets, sql, parameters, limits)})
    except Exception as exc:
        output.put({"ok": False, "error": str(exc)[:512]})


def _execute_scalar(
    datasets: str | Mapping[str, str], sql: str, parameters: dict[str, object] | None, limits: LocalReplayLimits,
    allowed_roots: tuple[str, ...] = (),
) -> str:
    """Shared DuckDB body; callers choose process isolation appropriate to their host."""
    import duckdb

    paths = normalize_datasets(datasets, limits, allowed_roots)
    try:
        query = validate_metric_sql(sql, allowed_tables=set(paths))
    except ValueError as exc:
        raise LocalReplayError(str(exc)) from exc
    connection = duckdb.connect(":memory:")
    try:
        connection.execute(f"SET memory_limit = '{limits.memory_limit}'")
        connection.execute(f"SET threads = {max(1, min(limits.threads, 32))}")
        for name, source in paths.items():
            escaped = source.as_posix().replace("'", "''")
            reader = "read_parquet" if source.suffix.lower() == ".parquet" else "read_csv_auto"
            connection.execute(f"CREATE VIEW \"{name}\" AS SELECT * FROM {reader}('{escaped}')")
        row = connection.execute(query, parameters or {}).fetchone()
        if row is None or len(row) != 1 or row[0] is None:
            raise LocalReplayError("Metric SQL must return exactly one non-null scalar.")
        value = Decimal(str(row[0]))
        if not value.is_finite():
            raise LocalReplayError("Metric SQL returned a non-finite numeric value.")
        serialized = str(value)
        if len(serialized.encode("utf-8")) > limits.max_result_bytes:
            raise LocalReplayError("Metric result exceeds the configured output limit.")
        return serialized
    finally:
        connection.close()


def execute_local_scalar(
    datasets: str | Mapping[str, str],
    sql: str,
    limits: LocalReplayLimits = LocalReplayLimits(),
    parameters: dict[str, object] | None = None,
    allowed_roots: tuple[str, ...] = (),
) -> Decimal:
    paths = normalize_datasets(datasets, limits, allowed_roots)
    try:
        validate_metric_sql(sql, allowed_tables=set(paths))
    except ValueError as exc:
        raise LocalReplayError(str(exc)) from exc
    context = mp.get_context("spawn")
    output = context.Queue(maxsize=1)
    process = context.Process(
        target=_child,
        args=({name: str(path) for name, path in paths.items()}, sql, parameters, limits, output),
    )
    process.start()
    process.join(limits.timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(5)
        raise LocalReplayError("Metric execution exceeded its wall-clock limit and was terminated.")
    try:
        message = output.get_nowait()
    except Empty as exc:
        raise LocalReplayError("Metric execution ended without a result.") from exc
    if not message["ok"]:
        raise LocalReplayError(message["error"])
    try:
        return Decimal(message["value"])
    except InvalidOperation as exc:
        raise LocalReplayError("Metric SQL did not return a decimal-compatible scalar.") from exc


def run_local_four_way(
    old_datasets: str | Mapping[str, str],
    new_datasets: str | Mapping[str, str],
    old_sql: str,
    new_sql: str,
    limits: LocalReplayLimits = LocalReplayLimits(),
    parameters: dict[str, object] | None = None,
    allowed_roots: tuple[str, ...] = (),
) -> dict:
    """Run all four actual cells; no missing or failed value is interpreted as zero."""
    a = execute_local_scalar(old_datasets, old_sql, limits, parameters, allowed_roots)
    b = execute_local_scalar(old_datasets, new_sql, limits, parameters, allowed_roots)
    c = execute_local_scalar(new_datasets, old_sql, limits, parameters, allowed_roots)
    d = execute_local_scalar(new_datasets, new_sql, limits, parameters, allowed_roots)
    return {
        "cells": {
            "old_data_old_definition": str(a),
            "old_data_new_definition": str(b),
            "new_data_old_definition": str(c),
            "new_data_new_definition": str(d),
        },
        "attribution": four_way_attribution(a, b, c, d),
    }


def run_local_four_way_in_process(
    old_datasets: str | Mapping[str, str], new_datasets: str | Mapping[str, str], old_sql: str, new_sql: str,
    limits: LocalReplayLimits = LocalReplayLimits(), parameters: dict[str, object] | None = None,
    allowed_roots: tuple[str, ...] = (),
) -> dict:
    """Shared calculation for a clean worker subprocess; not a public in-process sandbox."""
    a = Decimal(_execute_scalar(old_datasets, old_sql, parameters, limits, allowed_roots))
    b = Decimal(_execute_scalar(old_datasets, new_sql, parameters, limits, allowed_roots))
    c = Decimal(_execute_scalar(new_datasets, old_sql, parameters, limits, allowed_roots))
    d = Decimal(_execute_scalar(new_datasets, new_sql, parameters, limits, allowed_roots))
    return {
        "cells": {
            "old_data_old_definition": str(a), "old_data_new_definition": str(b),
            "new_data_old_definition": str(c), "new_data_new_definition": str(d),
        },
        "attribution": four_way_attribution(a, b, c, d),
    }


def inspect_datasets(
    datasets: str | Mapping[str, str],
    limits: LocalReplayLimits = LocalReplayLimits(),
    allowed_roots: tuple[str, ...] = (),
) -> dict[str, dict[str, object]]:
    """Return no-record schema metadata for explicitly authorized dataset files."""
    import duckdb

    paths = normalize_datasets(datasets, limits, allowed_roots)
    connection = duckdb.connect(":memory:")
    try:
        result: dict[str, dict[str, object]] = {}
        for name, source in paths.items():
            escaped = source.as_posix().replace("'", "''")
            reader = "read_parquet" if source.suffix.lower() == ".parquet" else "read_csv_auto"
            columns = connection.execute(f"DESCRIBE SELECT * FROM {reader}('{escaped}')").fetchall()
            result[name] = {
                "columns": [{"name": row[0], "type": str(row[1]).upper()} for row in columns],
                "format": source.suffix.lower().lstrip("."),
                "size_bytes": source.stat().st_size,
            }
        return result
    finally:
        connection.close()


def compare_dataset_schemas(old: Mapping[str, dict], new: Mapping[str, dict]) -> dict[str, object]:
    """Strictly compare names and types; never guess renames."""
    diagnostics: list[dict[str, object]] = []
    for name in sorted(set(old) | set(new)):
        if name not in old:
            diagnostics.append({"table": name, "kind": "added_table"})
            continue
        if name not in new:
            diagnostics.append({"table": name, "kind": "missing_table"})
            continue
        old_columns = {column["name"]: column["type"] for column in old[name]["columns"]}
        new_columns = {column["name"]: column["type"] for column in new[name]["columns"]}
        for column in sorted(set(old_columns) - set(new_columns)):
            diagnostics.append({"table": name, "column": column, "kind": "removed_column"})
        for column in sorted(set(new_columns) - set(old_columns)):
            diagnostics.append({"table": name, "column": column, "kind": "added_column"})
        for column in sorted(set(old_columns) & set(new_columns)):
            if old_columns[column] != new_columns[column]:
                diagnostics.append(
                    {
                        "table": name,
                        "column": column,
                        "kind": "type_change",
                        "old": old_columns[column],
                        "new": new_columns[column],
                    }
                )
    return {
        "compatible": not diagnostics,
        "diagnostics": diagnostics,
        "rename_detection": "disabled_without_explicit_mapping",
    }
