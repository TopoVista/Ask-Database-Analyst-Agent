from __future__ import annotations

import json

from app.agents.base import BaseAgent
from app.tools.schema_inspector import SchemaInspector
from app.tools.sql_executor import SQLExecutor


SIM_SYSTEM_PROMPT = """You are a business simulation expert.
Given a what-if scenario and database schema, generate SQL queries that:
1. Establish baseline metrics (current state)
2. Apply the hypothetical change mathematically
3. Calculate projected impact on KPIs
4. Identify second-order effects

Return JSON with simulation_plan containing steps with SQL and calculations.
Use CTE-based SQL where the change is applied as a multiplication/addition factor.
Never modify actual data — use derived calculations in SELECT."""


class SimulationAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(llm_service)
        self.executor = SQLExecutor()

    async def run(self, question: str, parameters: dict, connection_string: str):
        schema = await SchemaInspector().get_schema(connection_string)
        schema_str = SchemaInspector().to_prompt_string(schema)

        yield {"type": "step", "data": {"message": "Analyzing current baseline..."}}

        sim_plan_raw = await self.llm.complete(
            system_prompt=SIM_SYSTEM_PROMPT,
            user_prompt=f"Scenario: {question}\nParameters: {json.dumps(parameters, default=str)}\nSchema:\n{schema_str}",
            temperature=0.1,
            max_tokens=2000,
        )

        try:
            sim_plan = json.loads(sim_plan_raw)
        except Exception:
            yield {"type": "error", "data": {"message": "Failed to generate simulation plan"}}
            return

        results = []
        for step in sim_plan.get("simulation_plan", []):
            yield {"type": "step", "data": {"message": step.get("description", "Running simulation query...")}}
            exec_result = await self.executor.execute(connection_string, step["sql"])
            results.append({"step": step, "result": exec_result})
            yield {
                "type": "sim_result",
                "data": {
                    "label": step.get("label"),
                    "rows": exec_result.get("rows", [])[:20],
                    "columns": exec_result.get("columns", []),
                },
            }

        narrative_prompt = f"""Original question: {question}
Change parameters: {json.dumps(parameters, default=str)}
Simulation results: {json.dumps([{"step": r["step"].get("label"), "data": r["result"].get("rows", [])[:5]} for r in results], default=str)}

Write a concise business narrative explaining:
1. Current state baseline
2. Projected impact of the change
3. Key risks and assumptions
4. Recommended actions"""

        async for token in self.llm.stream_complete(
            system_prompt="You are a business analyst explaining simulation results. Be specific with numbers.",
            user_prompt=narrative_prompt,
        ):
            yield {"type": "insight_token", "data": {"token": token}}

        yield {"type": "done", "data": {}}

