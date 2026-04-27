from __future__ import annotations

from app.agents.base import BaseAgent
from app.tools.sql_validator import validate_sql


SQL_GEN_SYSTEM_PROMPT = """You are an expert PostgreSQL query writer.

Rules:
- Write only valid PostgreSQL syntax
- Always use table aliases
- Use CTEs for complex queries
- Never use SELECT * — specify columns explicitly
- Always include appropriate WHERE clauses for time filtering
- Use date_trunc for time grouping
- Return ONLY the SQL query, no explanation, no markdown backticks

For time periods, use:
- "last month": WHERE date_col >= date_trunc('month', NOW() - INTERVAL '1 month') AND date_col < date_trunc('month', NOW())
- "this month": WHERE date_col >= date_trunc('month', NOW())
- "last week": WHERE date_col >= NOW() - INTERVAL '7 days'"""

SQL_FIX_SYSTEM_PROMPT = """You are an expert PostgreSQL debugger.
Given a failing SQL query and its error, return ONLY the corrected SQL query.
No explanation. No markdown. Just the fixed SQL."""


def _strip_sql_fences(sql: str) -> str:
    cleaned = sql.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
        if cleaned.lower().startswith("sql"):
            cleaned = cleaned[3:]
        cleaned = cleaned.strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    return cleaned.strip()


class SQLGeneratorAgent(BaseAgent):
    async def run(
        self,
        task: dict,
        schema_context: str,
        previous_results: list[dict],
        max_retries: int = 3,
    ) -> dict:
        context_str = ""
        if previous_results:
            context_str = "\nPrevious query results context:\n"
            for result in previous_results[-2:]:
                context_str += f"- {result.get('task_description', 'Task')}: {str(result.get('sample', result.get('rows', [])))[:200]}\n"

        prompt = f"""Task: {task['description']}
Purpose: {task.get('purpose', '')}
Schema:
{schema_context}
{context_str}"""

        sql = await self.llm.complete(
            system_prompt=SQL_GEN_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.0,
            max_tokens=1000,
            use_cache=False,
        )
        sql = _strip_sql_fences(sql)
        validation = validate_sql(sql)
        if not validation.is_valid:
            self.logger.warning("sql_syntax_invalid_pre_execution", error=validation.reason)
        return {"task_id": task["id"], "task_description": task["description"], "sql": validation.normalized_sql or sql}

    async def fix_sql(self, sql: str, error: str, schema_context: str) -> str:
        prompt = f"""Failing SQL:
{sql}

Error: {error}

Schema context:
{schema_context}"""
        fixed = await self.llm.complete(
            system_prompt=SQL_FIX_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.0,
            max_tokens=800,
            use_cache=False,
        )
        fixed = _strip_sql_fences(fixed)
        validation = validate_sql(fixed)
        return validation.normalized_sql if validation.is_valid else "SELECT 1 AS value LIMIT 1"
