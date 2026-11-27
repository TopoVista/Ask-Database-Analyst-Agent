"""Deterministic, bounded dataset comparison for CSV and Parquet inputs."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from metrictrace_sdk.local_replay import LocalReplayError, LocalReplayLimits, normalize_datasets


class DatasetDiffError(RuntimeError):
    """Stable error for invalid dataset-comparison inputs."""


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _reader(path: Path) -> str:
    escaped = path.as_posix().replace("'", "''")
    reader = "read_parquet" if path.suffix.lower() == ".parquet" else "read_csv_auto"
    return f"{reader}('{escaped}')"


def _schema(connection: Any, view: str) -> list[dict[str, str]]:
    return [{"name": row[0], "type": str(row[1]).upper()} for row in connection.execute(f"DESCRIBE {view}").fetchall()]


def _schema_diff(old_schema: list[dict[str, str]], new_schema: list[dict[str, str]]) -> list[dict[str, str]]:
    old = {column["name"]: column["type"] for column in old_schema}
    new = {column["name"]: column["type"] for column in new_schema}
    changes: list[dict[str, str]] = []
    for name in sorted(old.keys() - new.keys()):
        changes.append({"kind": "removed_column", "column": name, "old_type": old[name]})
    for name in sorted(new.keys() - old.keys()):
        changes.append({"kind": "added_column", "column": name, "new_type": new[name]})
    for name in sorted(old.keys() & new.keys()):
        if old[name] != new[name]:
            changes.append({"kind": "type_change", "column": name, "old_type": old[name], "new_type": new[name]})
    return changes


def _fingerprint(old_path: Path, new_path: Path, keys: list[str], old_schema: list[dict[str, str]], new_schema: list[dict[str, str]]) -> str:
    payload = {
        "old": {"path": str(old_path), "size": old_path.stat().st_size, "mtime_ns": old_path.stat().st_mtime_ns},
        "new": {"path": str(new_path), "size": new_path.stat().st_size, "mtime_ns": new_path.stat().st_mtime_ns},
        "keys": keys,
        "old_schema": old_schema,
        "new_schema": new_schema,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _validate_keys(connection: Any, keys: list[str], old_columns: set[str], new_columns: set[str]) -> dict[str, Any]:
    missing_old, missing_new = sorted(set(keys) - old_columns), sorted(set(keys) - new_columns)
    if missing_old or missing_new:
        raise DatasetDiffError(f"Key columns are missing: old={missing_old}, new={missing_new}.")
    quoted = ", ".join(_quote(key) for key in keys)
    null_predicate = " OR ".join(f"{_quote(key)} IS NULL" for key in keys)
    result: dict[str, Any] = {}
    for label in ("old_data", "new_data"):
        duplicate_groups = connection.execute(
            f"SELECT COUNT(*) FROM (SELECT {quoted} FROM {label} GROUP BY {quoted} HAVING COUNT(*) > 1)"
        ).fetchone()[0]
        null_rows = connection.execute(f"SELECT COUNT(*) FROM {label} WHERE {null_predicate}").fetchone()[0]
        result[label] = {"duplicate_key_groups": int(duplicate_groups), "null_key_rows": int(null_rows)}
    return result


def _multiset_summary(connection: Any, old_schema: list[dict[str, str]], new_schema: list[dict[str, str]]) -> dict[str, Any]:
    if old_schema != new_schema:
        return {
            "mode": "multiset",
            "comparable": False,
            "reason": "Multiset row comparison requires identical ordered schemas.",
            "inserted": None,
            "deleted": None,
        }
    inserted = connection.execute("SELECT COUNT(*) FROM (SELECT * FROM new_data EXCEPT ALL SELECT * FROM old_data)").fetchone()[0]
    deleted = connection.execute("SELECT COUNT(*) FROM (SELECT * FROM old_data EXCEPT ALL SELECT * FROM new_data)").fetchone()[0]
    old_count = connection.execute("SELECT COUNT(*) FROM old_data").fetchone()[0]
    new_count = connection.execute("SELECT COUNT(*) FROM new_data").fetchone()[0]
    return {
        "mode": "multiset",
        "comparable": True,
        "old_rows": int(old_count),
        "new_rows": int(new_count),
        "inserted": int(inserted),
        "deleted": int(deleted),
        "unchanged": int(old_count - deleted),
        "modified": None,
        "note": "Without stable keys, row-level correspondence and modified-column attribution are unavailable.",
    }


def compare_datasets(
    old_dataset: str,
    new_dataset: str,
    *,
    key_columns: Iterable[str] = (),
    limit: int = 100,
    offset: int = 0,
    limits: LocalReplayLimits = LocalReplayLimits(),
    allowed_roots: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Compare two authorized files without treating hashes as row identities.

    Stable key mode validates uniqueness and nullability before joining. Without
    keys, the result is explicitly a multiset comparison rather than a false
    row-level pairing.
    """
    if limit < 1 or limit > 1_000 or offset < 0:
        raise DatasetDiffError("limit must be between 1 and 1000 and offset must be non-negative.")
    try:
        paths = normalize_datasets({"old_data": old_dataset, "new_data": new_dataset}, limits, allowed_roots)
    except LocalReplayError as exc:
        raise DatasetDiffError(str(exc)) from exc
    keys = list(key_columns)
    if any(not isinstance(key, str) or not key for key in keys) or len(set(keys)) != len(keys):
        raise DatasetDiffError("Key columns must be unique non-empty names.")
    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover
        raise DatasetDiffError("Dataset comparison requires duckdb.") from exc
    connection = duckdb.connect(":memory:")
    try:
        connection.execute(f"SET memory_limit = '{limits.memory_limit}'")
        connection.execute(f"SET threads = {max(1, min(limits.threads, 32))}")
        connection.execute(f"CREATE VIEW old_data AS SELECT * FROM {_reader(paths['old_data'])}")
        connection.execute(f"CREATE VIEW new_data AS SELECT * FROM {_reader(paths['new_data'])}")
        old_schema, new_schema = _schema(connection, "old_data"), _schema(connection, "new_data")
        schema_changes = _schema_diff(old_schema, new_schema)
        fingerprint = _fingerprint(paths["old_data"], paths["new_data"], keys, old_schema, new_schema)
        response: dict[str, Any] = {
            "fingerprint": fingerprint,
            "old_schema": old_schema,
            "new_schema": new_schema,
            "schema_changes": schema_changes,
            "pagination": {"limit": limit, "offset": offset},
        }
        if not keys:
            response.update({"key_validation": None, "summary": _multiset_summary(connection, old_schema, new_schema), "records": []})
            return response
        old_columns, new_columns = {column["name"] for column in old_schema}, {column["name"] for column in new_schema}
        key_validation = _validate_keys(connection, keys, old_columns, new_columns)
        response["key_validation"] = key_validation
        if any(value["duplicate_key_groups"] or value["null_key_rows"] for value in key_validation.values()):
            response.update({
                "summary": {"mode": "stable_key", "comparable": False, "reason": "Stable key validation failed; no row matching was performed."},
                "records": [],
            })
            return response
        comparable_columns = sorted((old_columns & new_columns) - set(keys))
        old_key_present = " AND ".join(f"o.{_quote(key)} IS NOT NULL" for key in keys)
        new_key_present = " AND ".join(f"n.{_quote(key)} IS NOT NULL" for key in keys)
        join = " AND ".join(f"o.{_quote(key)} = n.{_quote(key)}" for key in keys)
        changed = " OR ".join(f"o.{_quote(column)} IS DISTINCT FROM n.{_quote(column)}" for column in comparable_columns) or "FALSE"
        classification = f"CASE WHEN NOT ({old_key_present}) THEN 'inserted' WHEN NOT ({new_key_present}) THEN 'deleted' WHEN {changed} THEN 'modified' ELSE 'unchanged' END"
        cte = f"WITH matched AS (SELECT {classification} AS change_kind FROM old_data o FULL OUTER JOIN new_data n ON {join})"
        row = connection.execute(
            cte + " SELECT COUNT(*) FILTER (WHERE change_kind = 'inserted'), COUNT(*) FILTER (WHERE change_kind = 'deleted'), COUNT(*) FILTER (WHERE change_kind = 'modified'), COUNT(*) FILTER (WHERE change_kind = 'unchanged') FROM matched"
        ).fetchone()
        response["summary"] = {
            "mode": "stable_key", "comparable": True,
            "inserted": int(row[0]), "deleted": int(row[1]), "modified": int(row[2]), "unchanged": int(row[3]),
        }
        selected = [f"{classification} AS change_kind"]
        selected += [f"COALESCE(o.{_quote(key)}, n.{_quote(key)}) AS {_quote(key)}" for key in keys]
        selected += [f"o.{_quote(column)} AS {_quote('old__' + column)}" for column in comparable_columns]
        selected += [f"n.{_quote(column)} AS {_quote('new__' + column)}" for column in comparable_columns]
        order = ", ".join(_quote(key) for key in keys)
        cursor = connection.execute(
            f"SELECT {', '.join(selected)} FROM old_data o FULL OUTER JOIN new_data n ON {join} "
            f"WHERE {classification} <> 'unchanged' ORDER BY {order} LIMIT ? OFFSET ?",
            [limit, offset],
        )
        names = [column[0] for column in cursor.description]
        rows = [dict(zip(names, values)) for values in cursor.fetchall()]
        records = []
        for row_data in rows:
            change_kind = row_data.pop("change_kind")
            old_values, new_values, changed_columns = {}, {}, []
            for column in comparable_columns:
                old_value, new_value = row_data.pop("old__" + column), row_data.pop("new__" + column)
                if change_kind == "modified" and old_value != new_value:
                    changed_columns.append(column)
                if change_kind != "inserted":
                    old_values[column] = _json_value(old_value)
                if change_kind != "deleted":
                    new_values[column] = _json_value(new_value)
            records.append({"kind": change_kind, "key": {key: _json_value(value) for key, value in row_data.items()}, "changed_columns": changed_columns, "old": old_values, "new": new_values})
        response["records"] = records
        return response
    finally:
        connection.close()


def dataset_diff_markdown(report: dict[str, Any]) -> str:
    """Render a compact human-readable view from the canonical JSON result."""
    summary = report["summary"]
    lines = ["# Dataset comparison", "", f"Fingerprint: `{report['fingerprint']}`", ""]
    if not summary.get("comparable"):
        lines.extend(["## Comparison unavailable", "", summary["reason"]])
    else:
        lines.extend([
            "## Summary", "",
            f"- Mode: {summary['mode']}",
            f"- Inserted: {summary.get('inserted')}",
            f"- Deleted: {summary.get('deleted')}",
            f"- Modified: {summary.get('modified')}",
            f"- Unchanged: {summary.get('unchanged')}",
        ])
    if report["schema_changes"]:
        lines.extend(["", "## Schema changes", ""])
        lines.extend(f"- {change['kind']}: `{change['column']}`" for change in report["schema_changes"])
    if report["records"]:
        lines.extend(["", "## Changed records", ""])
        lines.extend(f"- {row['kind']}: `{json.dumps(row['key'], sort_keys=True, default=str)}`" for row in report["records"])
    return "\n".join(lines) + "\n"
