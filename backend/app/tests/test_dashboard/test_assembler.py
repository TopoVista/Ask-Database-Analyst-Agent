"""Tests for dashboard assembler."""

from __future__ import annotations

import pytest

from app.dashboard.assembler import DashboardAssembler, _generate_narrative
from app.dashboard.specs import DashboardSpec


class TestGenerateNarrative:
    def test_empty_rows(self):
        result = _generate_narrative("bar", [], [], "Test")
        assert "No data available" in result

    def test_metric_single_row(self):
        rows = [{"total_sales": 1500}]
        result = _generate_narrative("metric", ["total_sales"], rows, "Total Sales")
        assert "total_sales" in result
        assert "1500" in result

    def test_line_chart(self):
        rows = [
            {"month": "Jan", "revenue": 100},
            {"month": "Feb", "revenue": 150},
            {"month": "Mar", "revenue": 120},
        ]
        result = _generate_narrative("line", ["month", "revenue"], rows, "Revenue Trend")
        assert "revenue" in result
        assert "3 data points" in result
        assert "increased" in result

    def test_bar_chart(self):
        rows = [
            {"category": "Electronics", "sales": 500},
            {"category": "Clothing", "sales": 300},
            {"category": "Food", "sales": 700},
        ]
        result = _generate_narrative("bar", ["category", "sales"], rows, "Sales by Category")
        assert "Food" in result
        assert "700" in result
        assert "leads" in result

    def test_scatter_chart(self):
        rows = [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
        result = _generate_narrative("scatter", ["x", "y"], rows, "Correlation")
        assert "x" in result
        assert "y" in result
        assert "2 points" in result

    def test_table_chart(self):
        rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        result = _generate_narrative("table", ["a", "b"], rows, "Data Table")
        assert "2 rows" in result
        assert "2 columns" in result


class TestDashboardAssembler:
    def test_create_panel(self):
        assembler = DashboardAssembler()
        columns = ["category", "sales"]
        rows = [{"category": "A", "sales": 100}, {"category": "B", "sales": 200}]
        panel = assembler.create_panel(columns, rows, title="Sales by Category")

        assert panel.title == "Sales by Category"
        assert panel.chart_type == "bar"
        assert panel.narrative != ""
        assert len(panel.data) == 2

    def test_create_panel_metric(self):
        assembler = DashboardAssembler()
        columns = ["total"]
        rows = [{"total": 42}]
        panel = assembler.create_panel(columns, rows, title="Total")

        assert panel.chart_type == "metric"
        assert "42" in panel.narrative

    def test_assemble_single_result(self):
        assembler = DashboardAssembler(title="Sales Dashboard")
        result_sets = [
            {
                "columns": ["month", "revenue"],
                "rows": [
                    {"month": "Jan", "revenue": 100},
                    {"month": "Feb", "revenue": 200},
                ],
                "title": "Monthly Revenue",
            }
        ]
        spec = assembler.assemble(result_sets)

        assert isinstance(spec, DashboardSpec)
        assert spec.title == "Sales Dashboard"
        assert spec.panel_count == 1
        assert spec.panels[0].title == "Monthly Revenue"

    def test_assemble_multiple_results(self):
        assembler = DashboardAssembler(title="Multi Dashboard")
        result_sets = [
            {"columns": ["a", "b"], "rows": [{"a": 1, "b": 2}], "title": "Chart 1"},
            {"columns": ["c", "d"], "rows": [{"c": 3, "d": 4}], "title": "Chart 2"},
            {"columns": ["e", "f"], "rows": [{"e": 5, "f": 6}], "title": "Chart 3"},
        ]
        spec = assembler.assemble(result_sets)

        assert spec.panel_count == 3
        # First row: panels at col 0 and col 6
        assert spec.panels[0].layout.row == 0
        assert spec.panels[0].layout.col == 0
        assert spec.panels[1].layout.row == 0
        assert spec.panels[1].layout.col == 6
        # Second row: panel at col 0
        assert spec.panels[2].layout.row == 1
        assert spec.panels[2].layout.col == 0

    def test_assemble_with_summary(self):
        assembler = DashboardAssembler()
        result_sets = [
            {"columns": ["a"], "rows": [{"a": 1}], "title": "Test"},
        ]
        spec = assembler.assemble(result_sets, summary="Custom summary")

        assert spec.summary == "Custom summary"

    def test_assemble_generates_summary(self):
        assembler = DashboardAssembler()
        result_sets = [
            {"columns": ["a"], "rows": [{"a": 1}], "title": "Sales"},
            {"columns": ["b"], "rows": [{"b": 2}], "title": "Revenue"},
        ]
        spec = assembler.assemble(result_sets)

        assert "2 panels" in spec.summary
        assert "Sales" in spec.summary
        assert "Revenue" in spec.summary

    def test_assemble_empty_results(self):
        assembler = DashboardAssembler()
        spec = assembler.assemble([])

        assert spec.panel_count == 0
        assert spec.summary == ""

    def test_to_dict_serialization(self):
        assembler = DashboardAssembler(title="Test")
        result_sets = [
            {"columns": ["x", "y"], "rows": [{"x": 1, "y": 2}], "title": "Plot"},
        ]
        spec = assembler.assemble(result_sets)
        d = spec.to_dict()

        assert "id" in d
        assert "title" in d
        assert "panels" in d
        assert "summary" in d
        assert "layout_config" in d
        assert len(d["panels"]) == 1
