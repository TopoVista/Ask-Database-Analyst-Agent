from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agents.sql_generator_agent import SQLGeneratorAgent
from app.services.llm_service import LLMService


@pytest.fixture
def mock_llm():
    llm = AsyncMock(spec=LLMService)
    llm.complete = AsyncMock(return_value="SELECT date_trunc('month', created_at), SUM(profit) FROM orders WHERE created_at >= NOW() - INTERVAL '2 months' GROUP BY 1 ORDER BY 1")
    return llm


@pytest.mark.asyncio
async def test_sql_generator_produces_valid_sql(mock_llm):
    agent = SQLGeneratorAgent(mock_llm)
    result = await agent.run(
        task={"id": "T1", "description": "Get monthly profit for last 2 months"},
        schema_context="orders (id uuid, profit numeric, created_at timestamptz)",
        previous_results=[],
    )
    assert result["sql"] is not None
    assert "SELECT" in result["sql"].upper()
    assert result["task_id"] == "T1"


@pytest.mark.asyncio
async def test_sql_generator_strips_markdown_backticks(mock_llm):
    mock_llm.complete = AsyncMock(return_value="```sql\nSELECT 1\n```")
    agent = SQLGeneratorAgent(mock_llm)
    result = await agent.run(
        task={"id": "T1", "description": "Test"},
        schema_context="test (id int)",
        previous_results=[],
    )
    assert "```" not in result["sql"]

