from __future__ import annotations

import json

from app.agents.base import BaseAgent
from app.services.redaction import mask_pii_in_rows
from app.tools.chart_recommender import coerce_chart_spec, recommend_chart


CHART_RECOMMENDER_SYSTEM_PROMPT = """You are a data visualization expert.
Given the analytical task, query columns, and sample rows, recommend the single most appropriate chart.

Choose exactly one chart type from: line, bar, scatter, pie, metric, table.
Rules:
- time/date column paired with a numeric metric -> line
- categorical dimension paired with a numeric metric -> bar
- two numeric columns -> scatter
- a single numeric column with one row -> metric
- a single numeric column with many rows -> bar
- otherwise -> table

Do not invent column names — use only the columns provided.
Return ONLY valid JSON:
{"chart_type": "<type>", "x": "<column name or null>", "y": "<column name or null>", "title": "<short chart title>", "rationale": "<one sentence>"}"""


class ChartRecommenderAgent(BaseAgent):
    """EDA/visualization agent: recommends how to render a query result.

    Uses the LLM to pick a chart when available, with a deterministic
    rule-based recommender as the offline/parse-failure fallback.
    """

    async def run(
        self,
        columns: list[str],
        rows: list[dict],
        task_description: str | None = None,
    ) -> dict:
        safe_rows = mask_pii_in_rows(rows)[:8]
        prompt = f"""Task: {task_description or 'Visualize this result'}
Columns: {json.dumps(columns)}
Sample rows: {json.dumps(safe_rows, default=str)}"""

        try:
            response = await self.llm.complete(
                system_prompt=CHART_RECOMMENDER_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.0,
                max_tokens=400,
            )
            spec = coerce_chart_spec(json.loads(response))
            if spec is not None:
                return spec
        except Exception as exc:
            self.logger.warning("chart_recommender_fallback", error=str(exc))

        return recommend_chart(columns, safe_rows, task_description)