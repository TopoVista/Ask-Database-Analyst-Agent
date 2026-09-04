from __future__ import annotations

import time
from typing import AsyncGenerator

import structlog

from app.agents.chart_recommender_agent import ChartRecommenderAgent
from app.agents.hypothesis_agent import HypothesisAgent
from app.agents.insight_agent import InsightAgent
from app.agents.intent_agent import IntentAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.result_analyzer_agent import ResultAnalyzerAgent
from app.agents.sql_generator_agent import SQLGeneratorAgent
from app.memory.session_memory import SessionMemory
from app.memory.vector_memory import VectorMemory
from app.services.llm_service import LLMService
from app.tools.schema_inspector import SchemaInspector
from app.tools.sql_executor import SQLExecutor

logger = structlog.get_logger()


class AgentPipeline:
    def __init__(self):
        self.llm = LLMService()
        self.intent_agent = IntentAgent(self.llm)
        self.planner = PlannerAgent(self.llm)
        self.sql_gen = SQLGeneratorAgent(self.llm)
        self.result_analyzer = ResultAnalyzerAgent(self.llm)
        self.chart_recommender = ChartRecommenderAgent(self.llm)
        self.hypothesis_agent = HypothesisAgent(self.llm)
        self.insight_agent = InsightAgent(self.llm)
        self.executor = SQLExecutor()
        self.schema_inspector = SchemaInspector()

    async def run(
        self,
        user_question: str,
        connection_string: str,
        session_id: str,
        user_id: str,
        connection_id: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        start_time = time.monotonic()
        yield {"type": "step", "data": {"step": "schema_inspection", "message": "Reading database schema..."}}
        schema = await self.schema_inspector.get_schema(connection_string)
        schema_str = self.schema_inspector.to_prompt_string(schema)

        memory = SessionMemory(session_id)
        history = await memory.get_history()
        vector_memory = VectorMemory(user_id)
        similar_past = await vector_memory.search_similar(user_question, limit=3)

        yield {"type": "step", "data": {"step": "intent_classification", "message": "Understanding your question..."}}
        intent = await self.intent_agent.run(user_question, schema_str)
        yield {"type": "intent", "data": intent}

        yield {"type": "step", "data": {"step": "task_planning", "message": "Breaking down into sub-questions..."}}
        plan = await self.planner.run(user_question, intent, schema_str, history)
        yield {"type": "plan", "data": plan}

        query_results = []
        for task in plan.get("tasks", []):
            yield {
                "type": "step",
                "data": {"step": "sql_generation", "message": f"Generating query: {task['description'][:60]}..."},
            }
            sql_result = await self.sql_gen.run(task, schema_str, query_results)
            sql = sql_result["sql"]
            result = None
            for attempt in range(3):
                if sql is None:
                    result = {
                        **sql_result,
                        "success": False,
                        "rows": [],
                        "columns": [],
                        "row_count": 0,
                        "error": "Unable to produce a valid query for this step after repeated attempts. "
                        "Please rephrase the question or verify the table/column names against the schema.",
                    }
                    break
                exec_result = await self.executor.execute(connection_string, sql)
                if exec_result["success"]:
                    result = {**sql_result, **exec_result}
                    if result.get("columns") and result.get("rows"):
                        result["chart_spec"] = await self.chart_recommender.run(
                            result["columns"],
                            result["rows"],
                            task_description=result.get("task_description"),
                        )
                    break
                if attempt < 2:
                    yield {
                        "type": "step",
                        "data": {"step": "sql_correction", "message": f"Correcting SQL error (attempt {attempt + 2})..."},
                    }
                    sql = await self.sql_gen.fix_sql(sql, exec_result["error"], schema_str)
                else:
                    result = {**sql_result, "success": False, "rows": [], "columns": [], "row_count": 0, "error": exec_result["error"]}
            yield {
                "type": "query_result",
                "data": {
                    "task_id": task["id"],
                    "task_description": task["description"],
                    "sql": result["sql"],
                    "rows": result.get("rows", [])[:5],
                    "columns": result.get("columns", []),
                    "chart_spec": result.get("chart_spec"),
                    "success": result.get("success"),
                    "row_count": result.get("row_count", 0),
                    "error": result.get("error"),
                },
            }
            query_results.append(result)

        yield {"type": "step", "data": {"step": "result_analysis", "message": "Analyzing patterns and anomalies..."}}
        analysis = await self.result_analyzer.run(query_results)
        yield {"type": "analysis", "data": analysis}

        hypotheses = {"hypotheses": []}
        if intent.get("intent") == "diagnostic" and analysis.get("needs_deeper_investigation"):
            yield {"type": "step", "data": {"step": "hypothesis_generation", "message": "Generating hypotheses..."}}
            hypotheses = await self.hypothesis_agent.run(user_question, analysis, schema_str)
            for hyp in hypotheses.get("hypotheses", [])[:2]:
                yield {
                    "type": "step",
                    "data": {"step": "hypothesis_validation", "message": f"Validating: {hyp['hypothesis'][:60]}..."},
                }
                val_sql_result = await self.sql_gen.run({"id": "VAL", "description": hyp["validation_query"]}, schema_str, query_results)
                val_exec = await self.executor.execute(connection_string, val_sql_result["sql"])
                query_results.append({**val_sql_result, **val_exec, "is_validation": True})

        yield {"type": "step", "data": {"step": "insight_generation", "message": "Composing analysis..."}}
        full_insight = ""
        async for token in self.insight_agent.stream(
            user_question=user_question,
            intent=intent,
            plan=plan,
            query_results=query_results,
            analysis=analysis,
            similar_queries=similar_past,
        ):
            full_insight += token
            yield {"type": "insight_token", "data": {"token": token}}

        await memory.add_entry(user_question, full_insight)
        await vector_memory.store(user_question, full_insight, connection_id=connection_id)

        total_time = int((time.monotonic() - start_time) * 1000)
        yield {
            "type": "done",
            "data": {
                "execution_time_ms": total_time,
                "queries_executed": len(query_results),
                "anomalies_found": len(analysis.get("statistical_anomalies", [])),
                "final_insight": full_insight,
                "intent": intent,
                "plan": plan,
                "analysis": analysis,
                "hypotheses": hypotheses,
                "query_results": [
                    {
                        "task_id": result.get("task_id"),
                        "task_description": result.get("task_description"),
                        "sql": result.get("sql"),
                        "success": result.get("success"),
                        "row_count": result.get("row_count", 0),
                        "error": result.get("error"),
                    }
                    for result in query_results
                ],
            },
        }

