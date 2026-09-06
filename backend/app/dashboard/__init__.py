"""Automated dashboard generation package.

Provides dashboard spec models, layout generation, and narrative
assembly for multi-panel dashboard creation from query results.
"""

from app.dashboard.assembler import DashboardAssembler
from app.dashboard.specs import DashboardPanel, DashboardSpec, PanelLayout

__all__ = [
    "DashboardAssembler",
    "DashboardPanel",
    "DashboardSpec",
    "PanelLayout",
]
