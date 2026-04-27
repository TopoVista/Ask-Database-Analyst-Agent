from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import MetaData, Table, func, inspect, select, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine import URL

from app.config import get_settings


class SchemaInspector:
    async def get_schema(self, connection_string: str) -> dict[str, Any]:
        engine = create_async_engine(connection_string, future=True, pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                return await conn.run_sync(self._get_schema_sync)
        finally:
            await engine.dispose()

    def _get_schema_sync(self, sync_conn) -> dict[str, Any]:
        inspector = inspect(sync_conn)
        metadata = MetaData()
        schema: dict[str, Any] = {"tables": {}}
        for table_name in inspector.get_table_names(schema=None):
            table = Table(table_name, metadata, autoload_with=sync_conn)
            columns = []
            for column in table.columns:
                columns.append(
                    {
                        "name": column.name,
                        "type": str(column.type),
                        "nullable": bool(column.nullable),
                        "default": str(column.default.arg) if column.default is not None and getattr(column.default, "arg", None) is not None else None,
                    }
                )
            try:
                row_count = sync_conn.execute(select(func.count()).select_from(table)).scalar_one()
            except Exception:
                row_count = 0
            sample_rows = []
            try:
                result = sync_conn.execute(select(table).limit(3))
                sample_rows = [dict(row._mapping) for row in result.fetchall()]
            except Exception:
                sample_rows = []
            foreign_keys = []
            for fk in inspector.get_foreign_keys(table_name):
                target_table = fk.get("referred_table")
                referred_columns = fk.get("referred_columns") or []
                local_columns = fk.get("constrained_columns") or []
                if local_columns and target_table and referred_columns:
                    foreign_keys.append(
                        {
                            "column": local_columns[0],
                            "references": f"{target_table}.{referred_columns[0]}",
                        }
                    )
            schema["tables"][table_name] = {
                "columns": columns,
                "primary_keys": inspector.get_pk_constraint(table_name).get("constrained_columns", []),
                "foreign_keys": foreign_keys,
                "indexes": [index.get("name") for index in inspector.get_indexes(table_name)],
                "row_count_estimate": row_count,
                "sample_rows": sample_rows,
            }
        return schema

    def to_prompt_string(self, schema: dict) -> str:
        lines = ["DATABASE SCHEMA:"]
        for table_name, table_info in schema.get("tables", {}).items():
            lines.append(f"\n{table_name} (~{table_info.get('row_count_estimate', '?')} rows)")
            cols = ", ".join(
                f"{col['name']} ({col['type']}{'?' if col['nullable'] else ''})"
                for col in table_info.get("columns", [])
            )
            lines.append(f"  Columns: {cols}")
            if table_info.get("foreign_keys"):
                fk_text = ", ".join(
                    f"{fk['column']}→{fk['references']}" for fk in table_info["foreign_keys"]
                )
                lines.append(f"  FK: {fk_text}")
        return "\n".join(lines)

