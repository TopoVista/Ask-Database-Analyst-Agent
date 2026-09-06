"""Dashboard specification models.

Defines the data structures for multi-panel dashboards including
chart specs, layout metadata, and narrative text.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PanelLayout:
    """Layout positioning for a dashboard panel."""

    row: int = 0
    col: int = 0
    width: int = 6  # Grid columns (12-column grid)
    height: int = 4  # Grid rows

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DashboardPanel:
    """A single panel in a dashboard (chart, metric, or table)."""

    id: str
    title: str
    chart_type: str  # metric, line, bar, scatter, pie, table
    x: str | None = None
    y: str | None = None
    data: list[dict[str, Any]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    narrative: str = ""
    rationale: str = ""
    layout: PanelLayout = field(default_factory=PanelLayout)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "chart_type": self.chart_type,
            "x": self.x,
            "y": self.y,
            "data": self.data,
            "columns": self.columns,
            "narrative": self.narrative,
            "rationale": self.rationale,
            "layout": self.layout.to_dict(),
        }


@dataclass
class DashboardSpec:
    """Complete dashboard specification with multiple panels."""

    id: str
    title: str
    panels: list[DashboardPanel] = field(default_factory=list)
    summary: str = ""  # Overall dashboard narrative
    layout_config: dict[str, Any] = field(default_factory=lambda: {
        "columns": 12,
        "row_height": 80,
    })
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "panels": [p.to_dict() for p in self.panels],
            "summary": self.summary,
            "layout_config": self.layout_config,
            "metadata": self.metadata,
        }

    @property
    def panel_count(self) -> int:
        return len(self.panels)

    def add_panel(self, panel: DashboardPanel) -> None:
        """Add a panel and auto-assign layout position."""
        panel.layout.row = len(self.panels) // 2
        panel.layout.col = (len(self.panels) % 2) * 6
        self.panels.append(panel)
