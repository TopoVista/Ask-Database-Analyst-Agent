"""Conservative static SQL dependency and output-lineage inspection."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from metrictrace_sdk.core import validate_metric_sql


class LineageError(RuntimeError):
    """Stable error for a rejected static-lineage request."""


def _fingerprint(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _clean_tables(tables: Iterable[str]) -> set[str]:
    result = {table.strip().lower() for table in tables if table and table.strip()}
    if not result:
        raise LineageError("At least one explicitly authorized table is required.")
    return result


def _parse(sql: str, allowed_tables: set[str]):
    try:
        import sqlglot
        from sqlglot import exp

        cleaned = sql.strip().rstrip(";").strip()
        if not cleaned or ";" in cleaned:
            raise LineageError("Exactly one read-only SQL statement is required.")
        statement = sqlglot.parse_one(cleaned, dialect="duckdb")
        if not isinstance(statement, exp.Query):
            raise LineageError("Only SELECT or WITH queries can be inspected.")
        cte_names = {cte.alias_or_name.lower() for cte in statement.ctes if cte.alias_or_name}
        return statement, validate_metric_sql(cleaned, allowed_tables | cte_names), cte_names
    except LineageError:
        raise
    except ValueError as exc:
        raise LineageError(str(exc)) from exc
    except Exception as exc:
        raise LineageError(f"Unable to parse SQL lineage: {exc}") from exc


def _direct_sources(expression: Any, cte_names: set[str]) -> list[str]:
    from sqlglot import exp

    return sorted(
        {
            table.name.lower()
            for table in expression.find_all(exp.Table)
            if table.name and table.name.lower() not in cte_names
        }
    )


def _relation_aliases(statement: Any, cte_names: set[str]) -> tuple[dict[str, str], list[dict[str, str]]]:
    from sqlglot import exp

    aliases: dict[str, str] = {}
    uncertainty: list[dict[str, str]] = []
    for table in statement.find_all(exp.Table):
        relation = table.name.lower()
        alias = (table.alias_or_name or relation).lower()
        existing = aliases.get(alias)
        if existing is not None and existing != relation:
            uncertainty.append(
                {
                    "kind": "ambiguous_alias",
                    "detail": f"Alias {alias!r} resolves to both {existing!r} and {relation!r} across query scopes.",
                }
            )
            continue
        aliases[alias] = relation
    for subquery in statement.find_all(exp.Subquery):
        if subquery.alias_or_name:
            uncertainty.append(
                {
                    "kind": "derived_relation",
                    "detail": f"Derived relation {subquery.alias_or_name!r} is retained as static SQL context, not expanded into exact column lineage.",
                }
            )
    return aliases, uncertainty


def _output_columns(statement: Any, aliases: dict[str, str], cte_names: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    from sqlglot import exp

    uncertainty: list[dict[str, str]] = []
    outputs: list[dict[str, Any]] = []
    expressions = statement.args.get("expressions") or []
    for index, expression in enumerate(expressions, start=1):
        output_name = expression.alias_or_name or f"expression_{index}"
        columns: list[dict[str, str | None]] = []
        if expression.find(exp.Star):
            uncertainty.append(
                {
                    "kind": "star_projection",
                    "detail": f"Output {output_name!r} uses a star projection and cannot have exact column lineage without a schema.",
                }
            )
        for column in expression.find_all(exp.Column):
            qualifier = column.table.lower() if column.table else None
            relation = aliases.get(qualifier) if qualifier else None
            if qualifier and relation is None:
                uncertainty.append(
                    {
                        "kind": "unresolved_qualifier",
                        "detail": f"Column {column.sql(dialect='duckdb')!r} has no unambiguous relation alias.",
                    }
                )
            if not qualifier:
                uncertainty.append(
                    {
                        "kind": "unqualified_column",
                        "detail": f"Column {column.name!r} is unqualified and may be ambiguous across joined relations.",
                    }
                )
            columns.append(
                {
                    "relation": relation,
                    "column": column.name,
                    "relation_kind": "cte" if relation in cte_names else "base_table" if relation else "unresolved",
                }
            )
        functions = sorted({func.sql_name().upper() for func in expression.find_all(exp.Func)})
        outputs.append(
            {
                "name": output_name,
                "expression": expression.sql(dialect="duckdb"),
                "source_columns": sorted(columns, key=lambda item: ((item["relation"] or ""), item["column"])),
                "transformations": functions,
            }
        )
    return outputs, uncertainty


def inspect_sql_lineage(sql: str, allowed_tables: Iterable[str]) -> dict[str, Any]:
    """Return deterministic, conservative dependencies for one authorized query."""
    allowed = _clean_tables(allowed_tables)
    statement, normalized, cte_names = _parse(sql, allowed)
    aliases, uncertainty = _relation_aliases(statement, cte_names)
    outputs, output_uncertainty = _output_columns(statement, aliases, cte_names)
    uncertainty.extend(output_uncertainty)
    ctes = []
    for cte in statement.ctes:
        name = cte.alias_or_name.lower()
        ctes.append(
            {
                "name": name,
                "source_tables": _direct_sources(cte.this, cte_names),
                "expression": cte.this.sql(dialect="duckdb"),
            }
        )
    report: dict[str, Any] = {
        "normalized_sql": normalized,
        "source_tables": _direct_sources(statement, cte_names),
        "common_table_expressions": sorted(ctes, key=lambda item: item["name"]),
        "output_columns": outputs,
        "uncertainty": sorted(uncertainty, key=lambda item: (item["kind"], item["detail"])),
        "limitations": [
            "Static SQL lineage is dependency evidence, not runtime query-plan or row-level lineage.",
            "Dynamic SQL, external readers, write statements, and undeclared tables are rejected.",
        ],
    }
    report["fingerprint"] = _fingerprint(report)
    return report


def compare_sql_lineage(
    baseline_sql: str, candidate_sql: str, allowed_tables: Iterable[str]
) -> dict[str, Any]:
    """Compare static dependencies without claiming semantic equivalence."""
    baseline = inspect_sql_lineage(baseline_sql, allowed_tables)
    candidate = inspect_sql_lineage(candidate_sql, allowed_tables)
    baseline_outputs = {item["name"] for item in baseline["output_columns"]}
    candidate_outputs = {item["name"] for item in candidate["output_columns"]}
    change = {
        "source_tables": {
            "added": sorted(set(candidate["source_tables"]) - set(baseline["source_tables"])),
            "removed": sorted(set(baseline["source_tables"]) - set(candidate["source_tables"])),
        },
        "output_columns": {
            "added": sorted(candidate_outputs - baseline_outputs),
            "removed": sorted(baseline_outputs - candidate_outputs),
        },
        "definition_changed": baseline["normalized_sql"] != candidate["normalized_sql"],
    }
    report: dict[str, Any] = {"baseline": baseline, "candidate": candidate, "change": change}
    report["fingerprint"] = _fingerprint(report)
    return report
