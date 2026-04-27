from __future__ import annotations

import json

from app.agents.base import BaseAgent


INTENT_SYSTEM_PROMPT = """You are an intent classification expert for a data analytics system.

Classify the user's question and extract entities. Return ONLY valid JSON.

Intent types:
- diagnostic: "why did X happen", "what caused Y"
- exploratory: "show me X", "what is the trend of Y"
- comparative: "compare X vs Y", "how does X differ from Y"
- anomaly_detection: "are there anomalies", "anything unusual"
- simulation: "what if X", "if we change Y"
- predictive: "forecast", "predict next"

Return format:
{
  "intent": "<type>",
  "confidence": 0.0-1.0,
  "entities": {
    "metrics": ["profit", "revenue"],
    "time_period": "last month",
    "dimensions": ["product_category", "region"],
    "conditions": [],
    "comparison_period": "previous month"
  },
  "requires_multiple_queries": true/false,
  "complexity": "simple|medium|complex"
}"""


class IntentAgent(BaseAgent):
    async def run(self, user_question: str, schema_context: str) -> dict:
        response = await self.llm.complete(
            system_prompt=INTENT_SYSTEM_PROMPT,
            user_prompt=f"Question: {user_question}\n\nAvailable schema:\n{schema_context}",
            temperature=0.0,
            max_tokens=500,
        )
        try:
            return json.loads(response)
        except Exception:
            return {
                "intent": "exploratory",
                "confidence": 0.5,
                "entities": {"metrics": [], "time_period": None, "dimensions": [], "conditions": []},
                "requires_multiple_queries": False,
                "complexity": "simple",
            }

