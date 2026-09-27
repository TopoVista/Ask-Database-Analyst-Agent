from __future__ import annotations

import pytest

from app.specialists.dashboard_specialist import DashboardSpecialist


@pytest.mark.asyncio
async def test_dashboard_preserves_chart_recommender_spec():
    dashboard = await DashboardSpecialist().assemble_dashboard([
        {
            "success": True,
            "task_id": "T1",
            "task_description": "Compare revenue by region",
            "columns": ["region", "revenue"],
            "rows": [{"region": "North", "revenue": 42}, {"region": "South", "revenue": 21}],
            "chart_spec": {
                "chart_type": "bar", "x": "region", "y": "revenue",
                "title": "Revenue by region", "rationale": "Categories compared to a metric.",
            },
        }
    ])

    assert dashboard["panel_count"] == 1
    assert dashboard["panels"][0]["chart_type"] == "bar"
    assert dashboard["panels"][0]["chart_spec"]["chart_type"] == "bar"
