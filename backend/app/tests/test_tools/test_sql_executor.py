from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.tools.sql_executor import SQLExecutor


@pytest.mark.asyncio
async def test_sql_executor_returns_rows(tmp_path: Path):
    db_path = tmp_path / "executor.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, revenue REAL)")
    conn.executemany("INSERT INTO orders (revenue) VALUES (?)", [(100.0,), (150.5,), (90.0,)])
    conn.commit()
    conn.close()

    executor = SQLExecutor()
    result = await executor.execute(f"sqlite+aiosqlite:///{db_path}", "SELECT revenue FROM orders ORDER BY id")
    assert result["success"] is True
    assert result["row_count"] == 3
    assert result["rows"][0]["revenue"] == 100.0


@pytest.mark.asyncio
async def test_sql_executor_blocks_non_select(tmp_path: Path):
    db_path = tmp_path / "executor.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, revenue REAL)")
    conn.commit()
    conn.close()

    executor = SQLExecutor()
    result = await executor.execute(f"sqlite+aiosqlite:///{db_path}", "DELETE FROM orders")
    assert result["success"] is False
    assert "Only SELECT" in result["error"]

