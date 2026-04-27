from __future__ import annotations

import json

from app.agents.base import BaseAgent


PLANNER_SYSTEM_PROMPT = """You are a senior business analyst decomposing analytical questions into SQL-executable sub-tasks.

Given a user question, intent, and database schema, create a precise execution plan.

Rules:
- Each task must be answerable with a single SQL query
- Order tasks from broad to specific
- Maximum 6 tasks for complex questions
- Each task must have a clear analytical purpose
- Tasks should build on each other logically

Return ONLY valid JSON:
{
  "tasks": [
    {
      "id": "T1",
      "description": "Get total profit comparison: last month vs previous month",
      "purpose": "Establish baseline magnitude of change",
      "depends_on": [],
      "expected_output": "Two rows: current and previous month profit totals"
    }
  ],
  "analysis_strategy": "Start with macro view, drill down to contributors"
}"""


class PlannerAgent(BaseAgent):
    async def run(
        self,
        user_question: str,
        intent: dict,
        schema_context: str,
        session_history: list[str],
    ) -> dict:
        history_str = "\n".join(session_history[-5:]) if session_history else "None"
        prompt = f"""User Question: {user_question}
Intent: {json.dumps(intent)}
Previous queries in session: {history_str}

Schema:
{schema_context}"""
        response = await self.llm.complete(
            system_prompt=PLANNER_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.1,
            max_tokens=1500,
        )
        try:
            return json.loads(response)
        except Exception:
            return {
                "tasks": [{"id": "T1", "description": user_question, "purpose": "Answer the question", "depends_on": [], "expected_output": "Summary"}],
                "analysis_strategy": "Start broad and drill down.",
            }

