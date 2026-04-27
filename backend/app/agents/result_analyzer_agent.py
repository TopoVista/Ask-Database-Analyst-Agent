from __future__ import annotations

import json

from app.agents.base import BaseAgent
from app.tools.anomaly_detector import AnomalyDetector


ANALYZER_SYSTEM_PROMPT = """You are a quantitative data analyst.
Analyze SQL query results and identify:
1. Key trends (direction, magnitude, rate of change)
2. Notable outliers or anomalies
3. Statistical significance of changes
4. Patterns across dimensions

Return structured JSON analysis:
{
  "summary": "One sentence summary of what the data shows",
  "trends": [{"metric": str, "direction": "up|down|flat", "magnitude": str, "significance": "high|medium|low"}],
  "anomalies": [{"description": str, "severity": "high|medium|low", "value": any}],
  "key_findings": ["finding1", "finding2"],
  "needs_deeper_investigation": ["area1", "area2"]
}"""


class ResultAnalyzerAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(llm_service)
        self.anomaly_detector = AnomalyDetector()

    async def run(self, query_results: list[dict]) -> dict:
        statistical_anomalies = []
        results_summary = []
        for result in query_results:
            if result.get("success") and result.get("rows"):
                anomalies = self.anomaly_detector.detect(result["rows"], result["columns"])
                statistical_anomalies.extend(anomalies)
                results_summary.append(
                    {
                        "task": result.get("task_description", "Task"),
                        "row_count": result.get("row_count", len(result["rows"])),
                        "sample": result["rows"][:10],
                        "columns": result["columns"],
                    }
                )

        response = await self.llm.complete(
            system_prompt=ANALYZER_SYSTEM_PROMPT,
            user_prompt=f"Query results to analyze:\n{json.dumps(results_summary, indent=2, default=str)}",
            temperature=0.1,
            max_tokens=1500,
        )

        try:
            analysis = json.loads(response)
        except Exception:
            analysis = {
                "summary": "Analysis completed.",
                "trends": [],
                "anomalies": [],
                "key_findings": [],
                "needs_deeper_investigation": [],
            }

        analysis["statistical_anomalies"] = statistical_anomalies
        if not analysis.get("summary"):
            analysis["summary"] = "Analysis completed."
        return analysis

