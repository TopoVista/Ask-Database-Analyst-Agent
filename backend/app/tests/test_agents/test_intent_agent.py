from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agents.intent_agent import IntentAgent
from app.services.llm_service import LLMService


@pytest.fixture
def mock_llm():
    llm = AsyncMock(spec=LLMService)
    llm.complete = AsyncMock(
        return_value='{"intent":"diagnostic","confidence":0.9,"entities":{"metrics":["profit"],"time_period":"last month","dimensions":["region"],"conditions":[],"comparison_period":"previous month"},"requires_multiple_queries":true,"complexity":"complex"}'
    )
    return llm


@pytest.mark.asyncio
async def test_intent_agent_parses_json(mock_llm):
    agent = IntentAgent(mock_llm)
    result = await agent.run("Why did profit drop last month?", "orders table")
    assert result["intent"] == "diagnostic"
    assert result["entities"]["metrics"] == ["profit"]

