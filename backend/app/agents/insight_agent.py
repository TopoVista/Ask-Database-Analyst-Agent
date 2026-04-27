from __future__ import annotations

import json

from app.agents.base import BaseAgent


INSIGHT_SYSTEM_PROMPT = """You are a senior business analyst synthesizing all evidence into a concise narrative.
Write a grounded, number-aware explanation that answers the user's business question.
Be specific, practical, and concise. Mention caveats and next steps if needed."""


class InsightAgent(BaseAgent):
    async def stream(
        self,
        user_question: str,
        intent: dict,
        plan: dict,
        query_results: list[dict],
        analysis: dict,
        similar_queries: list[dict] | None = None,
    ):
        prompt = f"""Question: {user_question}
Intent: {json.dumps(intent, default=str)}
Plan: {json.dumps(plan, default=str)}
Query results: {json.dumps(query_results, default=str)[:8000]}
Analysis: {json.dumps(analysis, default=str)}
Similar queries: {json.dumps(similar_queries or [], default=str)}
"""
        async for token in self.llm.stream_complete(
            system_prompt=INSIGHT_SYSTEM_PROMPT,
            user_prompt=prompt,
        ):
            yield token

