"""Dashboard assembler: builds multi-panel dashboards from query results.

Combines chart recommendations, narrative generation, and layout
to produce complete dashboard specifications.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.dashboard.specs import DashboardPanel, DashboardSpec, PanelLayout
from app.tools.chart_recommender import recommend_chart


def _generate_narrative(
    chart_type: str,
    columns: list[str],
    rows: list[dict[str, Any]],
    title: str,
) -> str:
    """Generate a natural-language narrative for a chart.

    Produces a human-readable summary describing the data, highlighting
    key values, trends, or patterns.
    """
    if not rows:
        return f"No data available for '{title}'."

    narrative_parts: list[str] = []

    if chart_type == "metric":
        if rows and columns:
            value = list(rows[0].values())[0] if rows[0] else "N/A"
            metric_name = columns[-1] if columns else "value"
            narrative_parts.append(f"The {metric_name} is {value}.")
        else:
            narrative_parts.append(f"Metric: {title}.")

    elif chart_type == "line":
        y_col = None
        for col in columns:
            if any(isinstance(r.get(col), (int, float)) for r in rows if isinstance(r, dict)):
                y_col = col
                break
        if y_col and rows:
            values = [r[y_col] for r in rows if isinstance(r, dict) and isinstance(r.get(y_col), (int, float))]
            if values:
                narrative_parts.append(f"Showing {y_col} over {len(rows)} data points.")
                if len(values) >= 2:
                    first, last = values[0], values[-1]
                    if isinstance(first, (int, float)) and isinstance(last, (int, float)):
                        change = last - first
                        direction = "increased" if change > 0 else "decreased" if change < 0 else "remained stable"
                        narrative_parts.append(f"The value {direction} from {first} to {last}.")

    elif chart_type == "bar":
        y_col = None
        for col in columns:
            if any(isinstance(r.get(col), (int, float)) for r in rows if isinstance(r, dict)):
                y_col = col
                break
        if y_col and rows:
            values = [(r.get(y_col, 0), r.get(columns[0], "unknown")) for r in rows if isinstance(r, dict)]
            values.sort(key=lambda x: x[0] if isinstance(x[0], (int, float)) else 0, reverse=True)
            if values:
                top_val, top_name = values[0]
                narrative_parts.append(f"{top_name} leads with {top_val}, followed by {len(values) - 1} others.")

    elif chart_type == "scatter":
        narrative_parts.append(
            f"Scatter plot showing relationship between {columns[0] if columns else 'x'} "
            f"and {columns[1] if len(columns) > 1 else 'y'} across {len(rows)} points."
        )

    elif chart_type == "pie":
        narrative_parts.append(f"Distribution across {len(rows)} categories for '{title}'.")

    elif chart_type == "table":
        narrative_parts.append(f"Table with {len(rows)} rows and {len(columns)} columns.")

    return " ".join(narrative_parts) if narrative_parts else f"Chart: {title}."


class DashboardAssembler:
    """Assembles multi-panel dashboards from query results."""

    def __init__(self, title: str = "Dashboard") -> None:
        self.title = title

    def create_panel(
        self,
        columns: list[str],
        rows: list[dict[str, Any]],
        title: str = "Panel",
        narrative: str | None = None,
    ) -> DashboardPanel:
        """Create a single dashboard panel from query result data."""
        chart_spec = recommend_chart(columns, rows, task_description=title)

        auto_narrative = _generate_narrative(
            chart_spec["chart_type"], columns, rows, title
        )

        return DashboardPanel(
            id=uuid.uuid4().hex,
            title=title,
            chart_type=chart_spec["chart_type"],
            x=chart_spec.get("x"),
            y=chart_spec.get("y"),
            data=rows,
            columns=columns,
            narrative=narrative or auto_narrative,
            rationale=chart_spec.get("rationale", ""),
        )

    def assemble(
        self,
        result_sets: list[dict[str, Any]],
        *,
        summary: str | None = None,
    ) -> DashboardSpec:
        """Assemble a dashboard from multiple query result sets.

        Args:
            result_sets: List of dicts with keys:
                - columns: list[str]
                - rows: list[dict]
                - title: str (optional)
            summary: Optional overall dashboard summary.

        Returns:
            DashboardSpec with panels laid out in a grid.
        """
        spec = DashboardSpec(
            id=uuid.uuid4().hex,
            title=self.title,
        )

        for i, result in enumerate(result_sets):
            columns = result.get("columns", [])
            rows = result.get("rows", [])
            title = result.get("title", f"Panel {i + 1}")

            panel = self.create_panel(columns, rows, title=title)
            # Auto-layout: 2 columns, stacked vertically
            panel.layout = PanelLayout(
                row=i // 2,
                col=(i % 2) * 6,
                width=6,
                height=4,
            )
            spec.panels.append(panel)

        if summary:
            spec.summary = summary
        elif spec.panels:
            spec.summary = (
                f"Dashboard with {len(spec.panels)} panels covering "
                f"{', '.join(p.title for p in spec.panels[:3])}"
                f"{'...' if len(spec.panels) > 3 else ''}."
            )

        return spec
