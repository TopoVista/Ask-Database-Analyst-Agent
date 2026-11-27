"""Evidence-backed cardinality diagnostics for supported SQL joins."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from metrictrace_sdk.local_replay import LocalReplayError, LocalReplayLimits, normalize_datasets


class JoinAuditError(RuntimeError):
    """Stable error for join-audit configuration and SQL parsing failures."""


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _reader(path: Path) -> str:
    escaped = path.as_posix().replace("'", "''")
    return f"{'read_parquet' if path.suffix.lower() == '.parquet' else 'read_csv_auto'}('{escaped}')"


def _columns(expression: Any) -> list[Any]:
    from sqlglot import exp

    if isinstance(expression, exp.And):
        return _columns(expression.left) + _columns(expression.right)
    if isinstance(expression, exp.EQ) and isinstance(expression.left, exp.Column) and isinstance(expression.right, exp.Column):
        return [expression]
    return []


def _profile(connection: Any, table: str, columns: list[str]) -> dict[str, int]:
    quoted = ", ".join(_quote(column) for column in columns)
    null_check = " OR ".join(f"{_quote(column)} IS NULL" for column in columns)
    rows = connection.execute(f"SELECT COUNT(*) FROM {_quote(table)}").fetchone()[0]
    null_rows = connection.execute(f"SELECT COUNT(*) FROM {_quote(table)} WHERE {null_check}").fetchone()[0]
    distinct = connection.execute(f"SELECT COUNT(*) FROM (SELECT {quoted} FROM {_quote(table)} WHERE NOT ({null_check}) GROUP BY {quoted})").fetchone()[0]
    duplicates = connection.execute(f"SELECT COUNT(*) FROM (SELECT {quoted} FROM {_quote(table)} WHERE NOT ({null_check}) GROUP BY {quoted} HAVING COUNT(*) > 1)").fetchone()[0]
    return {"rows": int(rows), "distinct_non_null_keys": int(distinct), "duplicate_key_groups": int(duplicates), "null_key_rows": int(null_rows)}


def audit_sql_joins(
    datasets: Mapping[str, str], sql: str, *, limits: LocalReplayLimits = LocalReplayLimits(), allowed_roots: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Audit direct table equality joins; unsupported syntax returns uncertainty."""
    try:
        paths = normalize_datasets(datasets, limits, allowed_roots)
        import duckdb
        import sqlglot
        from sqlglot import exp
        statement = sqlglot.parse_one(sql.strip().rstrip(";"), dialect="duckdb")
    except (LocalReplayError, Exception) as exc:
        raise JoinAuditError(f"Unable to parse or authorize join audit: {exc}") from exc
    if not isinstance(statement, exp.Query):
        raise JoinAuditError("Only one SELECT or WITH query can be audited.")
    table_aliases: dict[str, str] = {}
    for table in statement.find_all(exp.Table):
        name = table.name.lower()
        alias = (table.alias_or_name or name).lower()
        if name not in paths:
            raise JoinAuditError(f"SQL references unauthorized table {name!r}.")
        table_aliases[alias] = name
    connection = duckdb.connect(":memory:")
    try:
        connection.execute(f"SET memory_limit = '{limits.memory_limit}'")
        connection.execute(f"SET threads = {max(1, min(limits.threads, 32))}")
        for name, path in paths.items():
            connection.execute(f"CREATE VIEW {_quote(name)} AS SELECT * FROM {_reader(path)}")
        schemas = {name: {row[0] for row in connection.execute(f"DESCRIBE {_quote(name)}").fetchall()} for name in paths}
        audits, uncertainty = [], []
        for index, join in enumerate(statement.find_all(exp.Join)):
            on = join.args.get("on")
            right = join.this
            if not isinstance(right, exp.Table) or on is None:
                uncertainty.append({"join_index": index, "reason": "Only direct table joins with ON equality predicates are profiled."})
                continue
            pairs = _columns(on)
            if not pairs:
                uncertainty.append({"join_index": index, "reason": "Join condition is not a conjunction of direct column equalities."})
                continue
            left_alias = pairs[0].left.table.lower() if pairs[0].left.table else ""
            right_alias = pairs[0].right.table.lower() if pairs[0].right.table else ""
            if left_alias not in table_aliases or right_alias not in table_aliases:
                uncertainty.append({"join_index": index, "reason": "Join aliases could not be resolved to authorized tables."})
                continue
            left_table, right_table = table_aliases[left_alias], table_aliases[right_alias]
            left_columns, right_columns = [], []
            valid = True
            for pair in pairs:
                if pair.left.table.lower() != left_alias or pair.right.table.lower() != right_alias:
                    valid = False
                    break
                left_columns.append(pair.left.name)
                right_columns.append(pair.right.name)
            if not valid or any(column not in schemas[left_table] for column in left_columns) or any(column not in schemas[right_table] for column in right_columns):
                uncertainty.append({"join_index": index, "reason": "Composite join aliases or columns are unsupported/unavailable."})
                continue
            predicate = " AND ".join(f"l.{_quote(left)} = r.{_quote(right)}" for left, right in zip(left_columns, right_columns))
            joined_rows = connection.execute(f"SELECT COUNT(*) FROM {_quote(left_table)} l JOIN {_quote(right_table)} r ON {predicate}").fetchone()[0]
            unmatched_left = connection.execute(f"SELECT COUNT(*) FROM {_quote(left_table)} l WHERE NOT EXISTS (SELECT 1 FROM {_quote(right_table)} r WHERE {predicate})").fetchone()[0]
            unmatched_right = connection.execute(f"SELECT COUNT(*) FROM {_quote(right_table)} r WHERE NOT EXISTS (SELECT 1 FROM {_quote(left_table)} l WHERE {predicate})").fetchone()[0]
            left_profile, right_profile = _profile(connection, left_table, left_columns), _profile(connection, right_table, right_columns)
            potential_amplification = joined_rows > max(left_profile["rows"], right_profile["rows"])
            audits.append({
                "join_index": index,
                "join_type": (join.args.get("side") or "INNER").upper(),
                "left": {"table": left_table, "columns": left_columns, "profile": left_profile},
                "right": {"table": right_table, "columns": right_columns, "profile": right_profile},
                "joined_rows": int(joined_rows), "unmatched_left_rows": int(unmatched_left), "unmatched_right_rows": int(unmatched_right),
                "potential_aggregate_amplification": bool(potential_amplification),
                "interpretation": "Cardinality evidence only; whether duplication is a defect requires business context.",
            })
        aggregates = [aggregate.sql(dialect="duckdb") for aggregate in statement.find_all(exp.AggFunc)]
        return {"supported": bool(audits), "joins": audits, "uncertainty": uncertainty, "aggregations": aggregates, "tables": sorted(paths)}
    finally:
        connection.close()
