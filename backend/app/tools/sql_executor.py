from __future__ import annotations

import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.tools.sql_validator import validate_sql


class SQLExecutor:
    async def execute(self, connection_string: str, sql: str, timeout: float = 30.0) -> dict[str, Any]:
        start = time.monotonic()
        settings = get_settings()
        validation = validate_sql(sql)
        if not validation.is_valid:
            return {
                "success": False,
                "rows": [],
                "columns": [],
                "row_count": 0,
                "error": validation.reason,
                "execution_time_ms": int((time.monotonic() - start) * 1000),
            }

        normalized_sql = validation.normalized_sql
        if "LIMIT" not in normalized_sql.upper():
            normalized_sql = f"{normalized_sql} LIMIT {settings.max_query_rows}"

        try:
            engine = create_async_engine(connection_string, future=True, pool_pre_ping=True)
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            return {
                "success": False,
                "rows": [],
                "columns": [],
                "row_count": 0,
                "error": f"Failed to create database engine: {str(exc)}",
                "execution_time_ms": elapsed,
            }

        try:
            async with engine.connect() as conn:
                result = await conn.execute(text(normalized_sql))
                rows = [dict(row._mapping) for row in result.fetchall()] if result.returns_rows else []
                columns = list(result.keys()) if result.returns_rows else []
                elapsed = int((time.monotonic() - start) * 1000)
                return {
                    "success": True,
                    "rows": rows,
                    "columns": columns,
                    "row_count": len(rows),
                    "error": None,
                    "execution_time_ms": elapsed,
                }
        except SQLAlchemyError as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            return {
                "success": False,
                "rows": [],
                "columns": [],
                "row_count": 0,
                "error": str(exc),
                "execution_time_ms": elapsed,
            }
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            return {
                "success": False,
                "rows": [],
                "columns": [],
                "row_count": 0,
                "error": f"Unexpected error: {str(exc)}",
                "execution_time_ms": elapsed,
            }
        finally:
            await engine.dispose()

