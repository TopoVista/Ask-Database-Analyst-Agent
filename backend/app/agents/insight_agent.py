from __future__ import annotations

import json

from app.agents.base import BaseAgent
from app.services.redaction import mask_pii_in_query_results


INSIGHT_SYSTEM_PROMPT = """You are a senior business analyst synthesizing all evidence into a concise narrative.
Write a grounded, number-aware explanation that answers the user's business question.
Be specific, practical, and concise. Mention caveats and next steps if needed."""


class InsightAgent(BaseAgent):
    def _build_prompt(
        self,
        user_question: str,
        intent: dict,
        plan: dict,
        query_results: list[dict],
        analysis: dict,
        similar_queries: list[dict] | None = None,
    ) -> str:
        return f"""Question: {user_question}
Intent: {json.dumps(intent, default=str)}
Plan: {json.dumps(plan, default=str)}
Query results: {json.dumps(mask_pii_in_query_results(query_results), default=str)[:8000]}
Analysis: {json.dumps(analysis, default=str)}
Similar queries: {json.dumps(similar_queries or [], default=str)}
"""

    async def run(
        self,
        user_question: str,
        intent: dict,
        plan: dict,
        query_results: list[dict],
        analysis: dict,
        similar_queries: list[dict] | None = None,
    ) -> str:
        prompt = self._build_prompt(
            user_question=user_question,
            intent=intent,
            plan=plan,
            query_results=query_results,
            analysis=analysis,
            similar_queries=similar_queries,
        )
        return await self.llm.complete(
            system_prompt=INSIGHT_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.2,
            max_tokens=3000,
            use_cache=False,
        )

    async def stream(
        self,
        user_question: str,
        intent: dict,
        plan: dict,
        query_results: list[dict],
        analysis: dict,
        similar_queries: list[dict] | None = None,
    ):
        prompt = self._build_prompt(
            user_question=user_question,
            intent=intent,
            plan=plan,
            query_results=query_results,
            analysis=analysis,
            similar_queries=similar_queries,
        )
        async for token in self.llm.stream_complete(
            system_prompt=INSIGHT_SYSTEM_PROMPT,
            user_prompt=prompt,
        ):
            yield token
