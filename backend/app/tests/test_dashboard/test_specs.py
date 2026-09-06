"""Tests for dashboard spec models."""

from __future__ import annotations

from app.dashboard.specs import DashboardPanel, DashboardSpec, PanelLayout


class TestPanelLayout:
    def test_default_values(self):
        layout = PanelLayout()
        assert layout.row == 0
        assert layout.col == 0
        assert layout.width == 6
        assert layout.height == 4

    def test_to_dict(self):
        layout = PanelLayout(row=1, col=2, width=4, height=3)
        d = layout.to_dict()
        assert d["row"] == 1
        assert d["col"] == 2
        assert d["width"] == 4
        assert d["height"] == 3


class TestDashboardPanel:
    def test_to_dict(self):
        panel = DashboardPanel(
            id="test-1",
            title="Sales",
            chart_type="bar",
            x="category",
            y="amount",
            data=[{"category": "A", "amount": 100}],
            columns=["category", "amount"],
            narrative="Test narrative",
            rationale="Test rationale",
        )
        d = panel.to_dict()
        assert d["id"] == "test-1"
        assert d["title"] == "Sales"
        assert d["chart_type"] == "bar"
        assert d["x"] == "category"
        assert d["y"] == "amount"
        assert d["data"] == [{"category": "A", "amount": 100}]
        assert d["columns"] == ["category", "amount"]
        assert d["narrative"] == "Test narrative"
        assert d["rationale"] == "Test rationale"
        assert "layout" in d

    def test_defaults(self):
        panel = DashboardPanel(id="p1", title="T", chart_type="table")
        assert panel.data == []
        assert panel.columns == []
        assert panel.narrative == ""
        assert panel.rationale == ""


class TestDashboardSpec:
    def test_to_dict(self):
        spec = DashboardSpec(id="d1", title="Test Dashboard")
        d = spec.to_dict()
        assert d["id"] == "d1"
        assert d["title"] == "Test Dashboard"
        assert d["panels"] == []
        assert d["summary"] == ""
        assert "layout_config" in d
        assert "metadata" in d

    def test_add_panel_autolayout(self):
        spec = DashboardSpec(id="d1", title="Test")
        panel1 = DashboardPanel(id="p1", title="P1", chart_type="bar")
        panel2 = DashboardPanel(id="p2", title="P2", chart_type="line")

        spec.add_panel(panel1)
        spec.add_panel(panel2)

        assert spec.panel_count == 2
        # First panel at row 0, col 0
        assert panel1.layout.row == 0
        assert panel1.layout.col == 0
        # Second panel at row 0, col 6
        assert panel2.layout.row == 0
        assert panel2.layout.col == 6

    def test_default_layout_config(self):
        spec = DashboardSpec(id="d1", title="Test")
        assert spec.layout_config["columns"] == 12
        assert spec.layout_config["row_height"] == 80
