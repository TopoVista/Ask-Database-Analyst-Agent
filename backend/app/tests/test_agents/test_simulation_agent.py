"""Regression tests for the deterministic, low-memory simulation path."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.agents.simulation_agent import SimulationAgent
from app.schemas.simulation import SimulationRequest


@pytest.mark.asyncio
async def test_simulation_runs_without_an_llm_and_projects_parameterized_metric(tmp_path):
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'scenario.db'}"
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE sales (id INTEGER PRIMARY KEY, revenue NUMERIC)"))
            await conn.execute(text("INSERT INTO sales (revenue) VALUES (100), (50)"))

        events = [
            event
            async for event in SimulationAgent().run(
                question="What if price increases by 10%?",
                parameters={"price_change_pct": 10},
                connection_string=database_url,
            )
        ]
    finally:
        await engine.dispose()

    assert not [event for event in events if event["type"] == "error"]
    projected = next(event for event in events if event["type"] == "sim_result" and event["data"]["label"] == "projected")
    row = projected["data"]["rows"][0]
    assert float(row["baseline_metric"]) == 150.0
    assert float(row["projected_metric"]) == 165.0
    assert events[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_simulation_uses_requested_metric_from_form(tmp_path):
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'metric_choice.db'}"
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE sales (revenue NUMERIC, price NUMERIC)"))
            await conn.execute(text("INSERT INTO sales (revenue, price) VALUES (100, 10), (50, 20)"))
        events = [event async for event in SimulationAgent().run(
            question="What if price increases?",
            parameters={"variable": "price", "change_type": "percentage", "change_value": 10},
            connection_string=database_url,
        )]
    finally:
        await engine.dispose()

    projected = next(event for event in events if event["type"] == "sim_result" and event["data"]["label"] == "projected")
    assert float(projected["data"]["rows"][0]["baseline_metric"]) == 30.0


def test_simulation_request_preserves_scenario_specific_parameters():
    request = SimulationRequest(
        question="What if prices rise?",
        connection_id="connection-id",
        parameters={"price_change_pct": 10},
    )
    assert request.parameters.model_dump()["price_change_pct"] == 10
