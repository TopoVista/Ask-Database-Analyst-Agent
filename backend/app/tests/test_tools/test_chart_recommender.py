"""Tests for the deterministic chart recommender tool."""

import pytest

from app.tools.chart_recommender import coerce_chart_spec, recommend_chart


def test_single_row_numeric_is_metric():
    spec = recommend_chart(["total_revenue"], [{"total_revenue": 1234}])
    assert spec["chart_type"] == "metric"
    assert spec["y"] == "total_revenue"


def test_time_plus_numeric_is_line():
    rows = [{"month": "2026-01", "revenue": 10}, {"month": "2026-02", "revenue": 20}]
    spec = recommend_chart(["month", "revenue"], rows)
    assert spec["chart_type"] == "line"
    assert spec["x"] == "month"
    assert spec["y"] == "revenue"


def test_categorical_plus_numeric_is_bar():
    rows = [{"region": "EU", "sales": 5}, {"region": "US", "sales": 9}]
    spec = recommend_chart(["region", "sales"], rows)
    assert spec["chart_type"] == "bar"
    assert spec["x"] == "region"
    assert spec["y"] == "sales"


def test_two_numeric_is_scatter():
    rows = [{"price": 1, "qty": 2}, {"price": 3, "qty": 4}]
    spec = recommend_chart(["price", "qty"], rows)
    assert spec["chart_type"] == "scatter"


def test_no_data_is_table():
    spec = recommend_chart([], [])
    assert spec["chart_type"] == "table"


def test_categorical_only_is_bar_with_null_y():
    rows = [{"status": "a"}, {"status": "b"}]
    spec = recommend_chart(["status"], rows)
    assert spec["chart_type"] == "bar"
    assert spec["x"] == "status"
    assert spec["y"] is None


def test_coerce_accepts_valid_spec():
    spec = coerce_chart_spec(
        {"chart_type": "bar", "x": "region", "y": "sales", "title": "T", "rationale": "R"}
    )
    assert spec is not None
    assert spec["chart_type"] == "bar"


def test_coerce_rejects_unknown_type_and_non_dict():
    assert coerce_chart_spec({"chart_type": "hologram", "x": None, "y": None}) is None
    assert coerce_chart_spec("not a dict") is None
    assert coerce_chart_spec(None) is None


def test_coerce_normalizes_non_string_axes():
    spec = coerce_chart_spec({"chart_type": "line", "x": 42, "y": ["a"], "title": None})
    assert spec is not None
    assert spec["x"] is None
    assert spec["y"] is None
    assert spec["title"]  # falls back to a non-empty default


@pytest.mark.parametrize(
    ("columns", "rows", "expected_type"),
    [
        (["created_at", "amount"], [{"created_at": "2026-01-01", "amount": 1}, {"created_at": "2026-01-02", "amount": 2}], "line"),
        (["region", "amount"], [{"region": "EU", "amount": 1}, {"region": "US", "amount": 2}], "bar"),
        (["amount"], [{"amount": 1}], "metric"),
    ],
)
def test_parametrized_shapes(columns, rows, expected_type):
    assert recommend_chart(columns, rows)["chart_type"] == expected_type
