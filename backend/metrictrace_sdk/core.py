"""Dependency-light deterministic computation shared by Lite and Platform."""
from __future__ import annotations
from decimal import Decimal


def four_way_attribution(a: Decimal, b: Decimal, c: Decimal, d: Decimal) -> dict[str, str | bool]:
    data_effect, definition_effect = c - a, b - a
    interaction_effect, total_change = d - c - b + a, d - a
    return {"data_effect": str(data_effect), "definition_effect": str(definition_effect), "interaction_effect": str(interaction_effect), "data_contribution": str((data_effect + d - b) / 2), "definition_contribution": str((definition_effect + d - c) / 2), "total_change": str(total_change), "reconciles": data_effect + definition_effect + interaction_effect == total_change}


def validate_metric_sql(sql: str, allowed_tables: set[str] | None = None) -> str:
    import sqlglot
    from sqlglot import exp
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned or ";" in cleaned:
        raise ValueError("Exactly one read-only SQL statement is required.")
    statements = sqlglot.parse(cleaned, dialect="duckdb")
    if len(statements) != 1 or not isinstance(statements[0], exp.Query):
        raise ValueError("Only SELECT or WITH queries are allowed.")
    if statements[0].find(exp.Into):
        raise ValueError("Only read-only SELECT queries are allowed.")
    blocked = {"read_csv", "read_csv_auto", "read_parquet", "read_json", "http_get", "load_extension", "install_extension", "attach", "glob", "env", "getenv", "pragma"}
    for func in statements[0].find_all(exp.Func):
        if func.sql_name().lower() in blocked or func.name.lower() in blocked:
            raise ValueError("Metric SQL may not access external files, URLs, extensions, or attachments.")
    tables = {table.name.lower() for table in statements[0].find_all(exp.Table)}
    allowed = {name.lower() for name in (allowed_tables or {"source_data"})}
    if tables - allowed:
        raise ValueError("Metric SQL references a table that was not explicitly authorized.")
    return cleaned
