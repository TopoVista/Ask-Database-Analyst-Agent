from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agents.planner_agent import PlannerAgent
from app.services.llm_service import LLMService


@pytest.fixture
def mock_llm():
    llm = AsyncMock(spec=LLMService)
    llm.complete = AsyncMock(
        return_value='{"tasks":[{"id":"T1","description":"Get profit","purpose":"Baseline","depends_on":[],"expected_output":"Totals"}],"analysis_strategy":"Start broad"}'
    )
    return llm


@pytest.mark.asyncio
async def test_planner_agent_parses_tasks(mock_llm):
    agent = PlannerAgent(mock_llm)
    result = await agent.run("Why did profit drop?", {"intent": "diagnostic"}, "orders table", [])
    assert result["tasks"][0]["id"] == "T1"
    assert "analysis_strategy" in result

