"""Dashboard Expert Specialist.

Assembles multi-panel dashboard descriptors from chart specs produced by the
pipeline and generates rule-based narrative summaries — no LLM required,
no heavy dependencies, safe on 512 MB Render free tier.
"""

from __future__ import annotations

from typing import Any

from app.core.registry import skill


def _rule_narrative(rows: list[Any], columns: list[str], title: str = "") -> str:
    """Generate a concise rule-based sentence from a query result set.

    Covers:
    - Single numeric column: min / max / average
    - Two columns (label + value): top item, bottom item
    - Otherwise: row count summary
    """
    if not rows or not columns:
        return "No data available for this panel."

    # Detect numeric columns
    numeric_cols: list[str] = []
    label_cols: list[str] = []
    for col in columns:
        sample_vals = [row[col] for row in rows if col in row and row[col] is not None]
        try:
            float(sample_vals[0])
            numeric_cols.append(col)
        except (ValueError, TypeError, IndexError):
            label_cols.append(col)

    n = len(rows)
    subject = title or "the data"

    if not numeric_cols:
        return f"{subject} contains {n} record{'s' if n != 1 else ''}."

    val_col = numeric_cols[0]
    values = []
    for row in rows:
        try:
            values.append(float(row[val_col]))
        except (ValueError, TypeError):
            pass

    if not values:
        return f"{subject} has {n} rows but no parseable numeric values."

    lo = min(values)
    hi = max(values)
    avg = sum(values) / len(values)
    trend = "flat"
    if len(values) >= 3:
        first_half = sum(values[: len(values) // 2]) / max(len(values) // 2, 1)
        second_half = sum(values[len(values) // 2 :]) / max(len(values) - len(values) // 2, 1)
        if second_half > first_half * 1.05:
            trend = "upward"
        elif second_half < first_half * 0.95:
            trend = "downward"

    parts: list[str] = []

    # Identify top/bottom label
    if label_cols:
        lbl = label_cols[0]
        val_rows = [(row.get(lbl, ""), row.get(val_col)) for row in rows if row.get(val_col) is not None]
        try:
            sorted_rows = sorted(val_rows, key=lambda x: float(x[1]), reverse=True)  # type: ignore[arg-type]
            top_lbl, top_val = sorted_rows[0]
            bot_lbl, bot_val = sorted_rows[-1]
            parts.append(
                f"Highest {val_col} is **{top_lbl}** ({float(top_val):,.2f}); "
                f"lowest is **{bot_lbl}** ({float(bot_val):,.2f})."
            )
        except Exception:
            pass

    parts.append(
        f"Range: {lo:,.2f}–{hi:,.2f} | Avg: {avg:,.2f} across {n} row{'s' if n != 1 else ''}."
    )
    if trend != "flat":
        parts.append(f"Overall {val_col} trend is **{trend}**.")

    return " ".join(parts)


def _infer_panel_title(task_description: str) -> str:
    """Derive a short panel title from the task description."""
    if not task_description:
        return "Panel"
    # Truncate and title-case
    short = task_description[:60].strip()
    if len(task_description) > 60:
        short += "…"
    return short


class DashboardSpecialist:
    """Dashboard Expert Specialist.

    Collects chart_specs and result rows from pipeline query_results and
    assembles a multi-panel dashboard descriptor with auto-generated narratives.
    """

    name: str = "dashboard_specialist"
    description: str = "Assemble multi-panel dashboards with rule-based auto-narrative"

    @skill("assemble_dashboard")
    async def assemble_dashboard(
        self,
        query_results: list[dict[str, Any]],
        dashboard_title: str = "Analysis Dashboard",
    ) -> dict[str, Any]:
        """Assemble a dashboard descriptor from pipeline query_results.

        Args:
            query_results: List of query result dicts (from pipeline).
            dashboard_title: Overall title for the dashboard.

        Returns:
            Dashboard descriptor with panels array.
        """
        panels: list[dict[str, Any]] = []
        kpi_summary: dict[str, Any] = {}

        for result in query_results:
            if not result.get("success"):
                continue

            rows = result.get("rows", [])
            columns = result.get("columns", [])
            chart_spec = result.get("chart_spec")
            task_desc = result.get("task_description", "")
            task_id = result.get("task_id", "")

            if not rows:
                continue

            narrative = _rule_narrative(rows, columns, title=task_desc)
            panel_title = _infer_panel_title(task_desc)

            panel: dict[str, Any] = {
                "id": task_id or f"panel_{len(panels) + 1}",
                "title": panel_title,
                "narrative": narrative,
                "row_count": result.get("row_count", len(rows)),
                "columns": columns,
                "preview_rows": rows[:5],
            }

            if chart_spec:
                panel["chart_spec"] = chart_spec
                panel["chart_type"] = chart_spec.get("type", "table")
            else:
                panel["chart_type"] = "table"

            # Build KPI cards for single-value results
            if len(rows) == 1 and len(columns) >= 1:
                for col in columns:
                    val = rows[0].get(col)
                    try:
                        kpi_summary[col] = float(val)  # type: ignore[arg-type]
                    except (TypeError, ValueError):
                        kpi_summary[col] = val

            panels.append(panel)

        return {
            "title": dashboard_title,
            "panel_count": len(panels),
            "panels": panels,
            "kpi_summary": kpi_summary,
        }

    @skill("generate_narrative")
    async def generate_narrative(
        self,
        rows: list[Any],
        columns: list[str],
        title: str = "",
    ) -> dict[str, Any]:
        """Generate a rule-based narrative for a single result set.

        Args:
            rows: List of row dicts.
            columns: Column names.
            title: Optional panel title for context.

        Returns:
            dict with `narrative` string.
        """
        text = _rule_narrative(rows, columns, title)
        return {"narrative": text, "row_count": len(rows), "column_count": len(columns)}

    @skill("suggest_layout")
    async def suggest_layout(
        self,
        panels: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Suggest a responsive grid layout for the given panels.

        Returns grid positions (col, row, width) for a 12-column grid.
        """
        layout: list[dict[str, Any]] = []
        col = 0
        row = 0
        for i, panel in enumerate(panels):
            chart_type = panel.get("chart_type", "table")
            # Wide panels for line/bar charts, half-width for KPI/pie
            if chart_type in ("line", "bar", "area"):
                width = 12
                if col > 0:
                    row += 1
                    col = 0
            elif chart_type in ("pie", "donut", "kpi"):
                width = 4
            else:
                width = 6

            if col + width > 12:
                row += 1
                col = 0

            layout.append(
                {
                    "panel_id": panel.get("id", f"panel_{i + 1}"),
                    "grid_col": col,
                    "grid_row": row,
                    "grid_width": width,
                }
            )
            col += width
            if col >= 12:
                col = 0
                row += 1

        return {"layout": layout, "rows": row + 1, "columns": 12}


def register() -> DashboardSpecialist:
    return DashboardSpecialist()
