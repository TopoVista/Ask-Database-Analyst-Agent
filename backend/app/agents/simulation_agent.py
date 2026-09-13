from __future__ import annotations

import math
from typing import Any

from app.tools.schema_inspector import SchemaInspector
from app.tools.sql_executor import SQLExecutor


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _factor_from_parameters(parameters: dict[str, Any]) -> float:
    """Derive a bounded multiplier from common what-if parameter names."""
    for key, value in parameters.items():
        key_text = str(key).lower()
        if not any(token in key_text for token in ("pct", "percent", "percentage")):
            continue
        try:
            percentage = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(percentage):
            return max(0.0, min(10.0, 1.0 + percentage / 100.0))
    try:
        value = float(parameters.get("change_value"))
    except (TypeError, ValueError):
        return 1.0
    if math.isfinite(value) and "percent" in str(parameters.get("change_type") or "").lower():
        return max(0.0, min(10.0, 1.0 + value / 100.0))
    return 1.0


def _numeric_column(table_info: dict[str, Any]) -> str | None:
    preferred = ("revenue", "sales", "profit", "amount", "price", "cost", "value", "quantity")
    columns = table_info.get("columns", [])
    for token in preferred:
        for column in columns:
            name = str(column.get("name") or "")
            if token in name.lower():
                return name
    for column in columns:
        column_type = str(column.get("type") or "").lower()
        if any(token in column_type for token in ("int", "numeric", "decimal", "real", "double", "float")):
            return str(column.get("name"))
    return None


def _deterministic_plan(schema: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
    tables = schema.get("tables") if isinstance(schema, dict) else None
    if not isinstance(tables, dict) or not tables:
        return {"simulation_plan": [], "assumptions": ["No readable tables were found in this connection."]}
    table_name, table_info = next(iter(tables.items()))
    table_sql = _quote_identifier(str(table_name))
    metric = _numeric_column(table_info if isinstance(table_info, dict) else {})
    factor = _factor_from_parameters(parameters)
    if metric:
        metric_sql = _quote_identifier(metric)
        baseline_sql = f"SELECT SUM(CAST({metric_sql} AS NUMERIC)) AS baseline_metric, COUNT(*) AS row_count FROM {table_sql}"
        projected_sql = (
            f"SELECT SUM(CAST({metric_sql} AS NUMERIC)) AS baseline_metric, "
            f"SUM(CAST({metric_sql} AS NUMERIC)) * {factor:.6f} AS projected_metric, "
            f"SUM(CAST({metric_sql} AS NUMERIC)) * {factor - 1:.6f} AS estimated_change FROM {table_sql}"
        )
        assumption = f"The selected metric '{metric}' changes proportionally by {(factor - 1) * 100:.2f}%."
    else:
        baseline_sql = f"SELECT COUNT(*) AS baseline_metric FROM {table_sql}"
        projected_sql = (
            f"SELECT COUNT(*) AS baseline_metric, COUNT(*) * {factor:.6f} AS projected_metric, "
            f"COUNT(*) * {factor - 1:.6f} AS estimated_change FROM {table_sql}"
        )
        assumption = "No numeric metric was detected, so the scenario projects record count only."
    return {
        "simulation_plan": [
            {"label": "baseline", "description": "Measure the current baseline.", "sql": baseline_sql},
            {"label": "projected", "description": "Apply the scenario without modifying source data.", "sql": projected_sql},
        ],
        "assumptions": [assumption, "This is a proportional what-if estimate, not a causal forecast."],
    }


def _narrative(results: list[dict[str, Any]], assumptions: list[str]) -> str:
    projected = next(
        (item.get("result", {}).get("rows", [{}])[0] for item in results if item.get("step", {}).get("label") == "projected"),
        {},
    )
    baseline, estimate, change = (projected.get("baseline_metric"), projected.get("projected_metric"), projected.get("estimated_change"))
    if baseline is not None and estimate is not None:
        summary = f"Baseline is {baseline}; the proportional scenario estimates {estimate}"
        if change is not None:
            summary += f" (change: {change})"
        summary += "."
    else:
        summary = "The scenario completed, but the selected table did not return a numeric baseline."
    return f"{summary} Assumptions: {' '.join(assumptions)}"


class SimulationAgent:
    """Run bounded, read-only what-if estimates without an LLM dependency.

    A scenario now generates two aggregate queries from the actual schema rather
    than asking an LLM to emit fragile JSON. This keeps it deterministic and
    safe to run on Render's 512 MB instance.
    """

    def __init__(self) -> None:
        self.executor = SQLExecutor()

    async def run(self, question: str, parameters: dict[str, Any], connection_string: str):
        del question  # The schema and structured parameters are the evidence.
        yield {"type": "step", "data": {"message": "Inspecting schema and preparing the baseline..."}}

        try:
            schema = await SchemaInspector().get_schema(connection_string)
            sim_plan = _deterministic_plan(schema, parameters)
        except Exception:
            yield {
                "type": "error",
                "data": {"message": "Unable to inspect this connection for simulation. Check that it is reachable and readable."},
            }
            return

        steps = sim_plan["simulation_plan"]
        if not steps:
            yield {"type": "error", "data": {"message": "No readable table is available for this simulation."}}
            return

        results: list[dict[str, Any]] = []
        for step in steps:
            yield {"type": "step", "data": {"message": step["description"]}}
            execution = await self.executor.execute(connection_string, step["sql"])
            result = {"step": step, "result": execution}
            results.append(result)
            if not execution["success"]:
                yield {"type": "error", "data": {"message": execution["error"] or "Simulation query failed."}}
                return
            yield {
                "type": "sim_result",
                "data": {
                    "label": step["label"],
                    "rows": execution["rows"][:20],
                    "columns": execution["columns"],
                },
            }

        narrative = _narrative(results, sim_plan["assumptions"])
        yield {"type": "insight_token", "data": {"token": narrative}}
        yield {
            "type": "done",
            "data": {
                "mode": "deterministic_proportional_estimate",
                "assumptions": sim_plan["assumptions"],
            },
        }
