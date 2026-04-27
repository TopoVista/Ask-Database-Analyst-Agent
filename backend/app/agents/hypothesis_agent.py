from __future__ import annotations

import json

from app.agents.base import BaseAgent


HYPOTHESIS_SYSTEM_PROMPT = """You are a hypothesis generation specialist for diagnostics.
Given the question, result analysis, and schema context, generate a small set of testable hypotheses.
Return ONLY valid JSON:
{
  "hypotheses": [
    {
      "hypothesis": "string",
      "validation_query": "string",
      "expected_signal": "string",
      "priority": "high|medium|low"
    }
  ]
}"""


class HypothesisAgent(BaseAgent):
    async def run(self, user_question: str, analysis: dict, schema_context: str) -> dict:
        prompt = f"""User Question: {user_question}
Analysis: {json.dumps(analysis, default=str)}
Schema:
{schema_context}"""
        response = await self.llm.complete(
            system_prompt=HYPOTHESIS_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.1,
            max_tokens=1200,
        )
        try:
            return json.loads(response)
        except Exception:
            return {
                "hypotheses": [
                    {
                        "hypothesis": "The change may be concentrated in one major segment.",
                        "validation_query": "SELECT 1 AS validation_signal LIMIT 1",
                        "expected_signal": "Concentration in a small slice",
                        "priority": "medium",
                    }
                ]
            }

