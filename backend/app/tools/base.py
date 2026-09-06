"""Base ``Tool`` Protocol and registry wiring for the existing tools.

Every tool in the system conforms (structurally) to the ``Tool`` Protocol
defined here.  The :class:`~app.core.registry.ToolRegistry` stores ``ToolSpec``
entries — metadata + an async ``executor`` callable — and existing tools are
registered through :func:`register_all_tools`.

The protocol is intentionally thin so that plain classes (SchemaInspector) and
wrapped functions (recommend_chart, validate_sql) can both participate.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.core.registry import ToolRegistry, ToolSpec
from app.tools.anomaly_detector import AnomalyDetector
from app.tools.chart_recommender import coerce_chart_spec, recommend_chart
from app.tools.schema_inspector import SchemaInspector
from app.tools.sql_executor import SQLExecutor
from app.tools.sql_validator import validate_sql

__all__ = ["Tool", "tool_registry", "register_all_tools"]


@runtime_checkable
class Tool(Protocol):
    """Structural interface for any tool the orchestration layer can call."""

    id: str
    name: str
    description: str

    async def execute(self, **kwargs: Any) -> Any:  # pragma: no cover
        ...


def _wrap_sync(fn, tool_id: str, tool_name: str) -> ToolSpec:
    """Wrap a synchronous callable into an async ``ToolSpec`` executor."""

    async def _execute(**kwargs: Any) -> Any:
        return fn(**kwargs)

    return ToolSpec(
        id=tool_id,
        name=tool_name,
        description=fn.__doc__ or tool_name,
        executor=_execute,
    )


# A module-level registry pre-populated with the five core tools.  The
# pipeline and specialist runners consult this registry to discover and invoke
# tools by id.
tool_registry = ToolRegistry()


def register_all_tools(registry: ToolRegistry | None = None) -> ToolRegistry:
    """Register every built-in tool into *registry* (or the default one)."""
    registry = registry or tool_registry

    # --- Schema Inspector ------------------------------------------------
    inspector = SchemaInspector()

    async def _inspect(**kwargs: Any) -> Any:
        conn = kwargs.get("connection_string", "")
        schema = await inspector.get_schema(conn)
        return {"schema": schema, "prompt_string": inspector.to_prompt_string(schema)}

    registry.register(
        ToolSpec(
            id="schema_inspector",
            name="Schema Inspector",
            description="Reads database schema (tables, columns, FKs, row counts, sample rows) and returns a prompt-friendly string.",
            input_schema={"connection_string": "str"},
            output_schema={"schema": "dict", "prompt_string": "str"},
            permissions=frozenset({"read"}),
            executor=_inspect,
        ),
        overwrite=True,
    )

    # --- SQL Executor ----------------------------------------------------
    executor = SQLExecutor()

    async def _run_sql(**kwargs: Any) -> Any:
        conn = kwargs.get("connection_string", "")
        sql = kwargs.get("sql", "")
        timeout = kwargs.get("timeout", 30.0)
        return await executor.execute(conn, sql, timeout=timeout)

    registry.register(
        ToolSpec(
            id="sql_executor",
            name="SQL Executor",
            description="Executes a read-only SQL query against a database connection and returns rows, columns, and row count.",
            input_schema={"connection_string": "str", "sql": "str"},
            output_schema={"rows": "list", "columns": "list", "row_count": "int"},
            permissions=frozenset({"read"}),
            executor=_run_sql,
        ),
        overwrite=True,
    )

    # --- SQL Validator ---------------------------------------------------
    registry.register(
        ToolSpec(
            id="sql_validator",
            name="SQL Validator",
            description="Parses SQL with sqlglot, blocks DML/DDL, and requires SELECT/WITH.",
            input_schema={"sql": "str"},
            output_schema={"is_valid": "bool", "reason": "str", "normalized_sql": "str"},
            permissions=frozenset({"read"}),
            executor=_wrap_sync(validate_sql, "sql_validator", "SQL Validator"),
        ),
        overwrite=True,
    )

    # --- Anomaly Detector ------------------------------------------------
    detector = AnomalyDetector()

    async def _detect(**kwargs: Any) -> Any:
        rows = kwargs.get("rows", [])
        columns = kwargs.get("columns", [])
        return detector.detect(rows, columns)

    registry.register(
        ToolSpec(
            id="anomaly_detector",
            name="Anomaly Detector",
            description="Detects z-score and IQR outliers in numeric result columns.",
            input_schema={"rows": "list[dict]", "columns": "list[str]"},
            output_schema={"anomalies": "list[dict]"},
            permissions=frozenset({"read"}),
            executor=_detect,
        ),
        overwrite=True,
    )

    # --- Chart Recommender ------------------------------------------------
    async def _chart(**kwargs: Any) -> Any:
        columns = kwargs.get("columns", [])
        rows = kwargs.get("rows", [])
        task = kwargs.get("task_description")
        spec = recommend_chart(columns, rows, task)
        return {"chart_spec": spec}

    registry.register(
        ToolSpec(
            id="chart_recommender",
            name="Chart Recommender",
            description="Recommends the best chart type (line/bar/scatter/pie/metric/table) for a result set.",
            input_schema={"columns": "list[str]", "rows": "list[dict]", "task_description": "str|None"},
            output_schema={"chart_spec": "dict"},
            permissions=frozenset({"read"}),
            executor=_chart,
        ),
        overwrite=True,
    )

    return registry


# Eagerly register all tools at import time so the default registry is
    # ready for use by the pipeline and API layer.
register_all_tools()
