"""Deterministic chart-spec recommendation for SQL query results.

Given the columns and rows returned by a query, this tool recommends the most
appropriate visualization (mirroring the auto-chart-selection rules from the
analytics-agent design): time + metric -> line, categorical + metric -> bar,
two numeric columns -> scatter, single headline value -> metric card.

It powers the LLM-backed ``ChartRecommenderAgent`` offline/rule-based fallback
and provides a sane baseline whenever a model response cannot be parsed.
"""

from __future__ import annotations

from typing import Any

ALLOWED_CHART_TYPES = {"metric", "line", "bar", "scatter", "pie", "table"}

_TIME_HINTS = {
    "date",
    "time",
    "day",
    "month",
    "year",
    "week",
    "period",
    "timestamp",
    "created",
    "updated",
    "posted",
    "occurred",
}
_METRIC_HINTS = {
    "amount",
    "revenue",
    "profit",
    "sales",
    "total",
    "sum",
    "price",
    "cost",
    "margin",
    "quantity",
    "count",
    "value",
    "rate",
    "score",
    "avg",
    "mean",
    "qty",
}


def _is_time_column(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in _TIME_HINTS)


def _is_numeric_value(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _infer_column_roles(columns: list[str], rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    numeric: list[str] = []
    categorical: list[str] = []
    time: list[str] = []
    for col in columns:
        values = [row.get(col) for row in rows if isinstance(row, dict)]
        if _is_time_column(col):
            time.append(col)
        if any(_is_numeric_value(v) for v in values):
            numeric.append(col)
        else:
            categorical.append(col)
    return {"time": time, "numeric": numeric, "categorical": categorical}


def recommend_chart(
    columns: list[str],
    rows: list[dict[str, Any]],
    task_description: str | None = None,
) -> dict[str, Any]:
    """Return a chart spec dict describing the best way to visualize the result."""
    title = (task_description or "Query result").strip().rstrip(".")
    if not columns or not rows:
        return {
            "chart_type": "table",
            "x": None,
            "y": None,
            "title": title,
            "rationale": "No data to chart; showing the result as a table.",
        }

    roles = _infer_column_roles(columns, rows)
    numeric = roles["numeric"]
    time = roles["time"]
    categorical = roles["categorical"]

    # Single headline value -> metric card.
    if len(rows) == 1 and numeric:
        return {
            "chart_type": "metric",
            "x": None,
            "y": numeric[0],
            "title": title,
            "rationale": "A single-row result reads best as a headline metric card.",
        }

    # Time + metric -> line chart.
    if time and numeric:
        return {
            "chart_type": "line",
            "x": time[0],
            "y": numeric[0],
            "title": title,
            "rationale": "A time column paired with a numeric metric is best shown as a trend line.",
        }

    # Two numeric columns -> scatter.
    if len(numeric) >= 2:
        return {
            "chart_type": "scatter",
            "x": numeric[0],
            "y": numeric[1],
            "title": title,
            "rationale": "Two numeric columns suggest a correlation scatter plot.",
        }

    # Categorical dimension + metric -> bar.
    if categorical and numeric:
        return {
            "chart_type": "bar",
            "x": categorical[0],
            "y": numeric[0],
            "title": title,
            "rationale": "A categorical dimension with a numeric metric reads best as bars.",
        }

    # Single categorical column -> bar over row counts.
    if categorical:
        return {
            "chart_type": "bar",
            "x": categorical[0],
            "y": None,
            "title": title,
            "rationale": "A single categorical column is shown as bars over row counts.",
        }

    return {
        "chart_type": "table",
        "x": None,
        "y": None,
        "title": title,
        "rationale": "The result did not map cleanly to a preferred chart type.",
    }


def coerce_chart_spec(spec: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and normalize an LLM-produced chart spec.

    Returns ``None`` when the spec is unusable (missing keys, unknown chart
    type, or non-string axis references) so callers can fall back to the
    rule-based recommender.
    """
    if not isinstance(spec, dict):
        return None
    chart_type = spec.get("chart_type")
    if chart_type not in ALLOWED_CHART_TYPES:
        return None
    return {
        "chart_type": chart_type,
        "x": spec.get("x") if isinstance(spec.get("x"), str) else None,
        "y": spec.get("y") if isinstance(spec.get("y"), str) else None,
        "title": str(spec.get("title") or "Query result"),
        "rationale": str(spec.get("rationale") or ""),
    }