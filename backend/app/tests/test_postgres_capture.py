from __future__ import annotations

import os
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.infrastructure.capture.postgres import (
    CaptureLimits,
    CaptureTable,
    PostgresSnapshotCapture,
    SnapshotCaptureError,
)
from app.infrastructure.storage.snapshot_store import LocalSnapshotStore


class _Transaction:
    def __init__(self, connection):
        self.connection = connection

    async def start(self):
        self.connection.events.append("transaction:start:repeatable_read:readonly")

    async def commit(self):
        self.connection.events.append("transaction:commit")


class _Connection:
    def __init__(self):
        self.events: list[str] = []

    def transaction(self, *, isolation=None, readonly):
        assert isolation in {None, "repeatable_read"}
        assert readonly is True
        return _Transaction(self)

    async def fetchval(self, query):
        self.events.append(query)
        return datetime(2026, 1, 1, tzinfo=timezone.utc) if "CURRENT_TIMESTAMP" in query else "1:1:"

    async def execute(self, query, *args):
        self.events.append(query)

    async def fetch(self, query, schema, table):
        if "information_schema.columns" in query:
            return [
                {"column_name": "id", "data_type": "integer", "udt_name": "int4", "is_nullable": "NO", "numeric_precision": 32, "numeric_scale": 0},
                {"column_name": "amount", "data_type": "numeric", "udt_name": "numeric", "is_nullable": "YES", "numeric_precision": 12, "numeric_scale": 2},
                {"column_name": "paid_at", "data_type": "timestamp with time zone", "udt_name": "timestamptz", "is_nullable": "YES", "numeric_precision": None, "numeric_scale": None},
                {"column_name": "order_date", "data_type": "date", "udt_name": "date", "is_nullable": "YES", "numeric_precision": None, "numeric_scale": None},
            ]
        if "PRIMARY KEY" in query:
            return [{"column_name": "id"}]
        if "FOREIGN KEY" in query:
            return []
        raise AssertionError(query)

    async def cursor(self, query, *, prefetch):
        assert '"sales"."orders"' in query
        assert prefetch == 1
        yield {"id": 1, "amount": Decimal("12.30"), "paid_at": datetime(2026, 1, 1, tzinfo=timezone.utc), "order_date": date(2026, 1, 1)}
        yield {"id": 2, "amount": None, "paid_at": None, "order_date": None}

    async def close(self):
        self.events.append("close")


@pytest.mark.asyncio
async def test_capture_uses_one_readonly_repeatable_read_snapshot_and_verified_immutable_objects(tmp_path):
    connection = _Connection()

    async def connect(dsn):
        assert dsn == "postgresql://user:password@example.test/database"
        return connection

    workspace_id, source_id = uuid4(), uuid4()
    capture = PostgresSnapshotCapture(
        LocalSnapshotStore(str(tmp_path)), CaptureLimits(batch_rows=1, max_rows=10, max_bytes=1_000_000), connect
    )
    result = await capture.capture(
        "postgresql+asyncpg://user:password@example.test/database",
        workspace_id,
        source_id,
        [CaptureTable("sales", "orders")],
    )

    store = LocalSnapshotStore(str(tmp_path))
    manifest = store.read_manifest(workspace_id, result.manifest_key)
    assert connection.events[:3] == [
        "transaction:start:repeatable_read:readonly",
        "SELECT txid_current_snapshot()",
        "SELECT CURRENT_TIMESTAMP",
    ]
    assert connection.events[3] == "SELECT set_config('statement_timeout', $1, true)"
    assert result.row_count == 2
    assert manifest["consistency_level"] == "postgresql_repeatable_read"
    assert manifest["source_snapshot_at"] == "2026-01-01T00:00:00+00:00"
    assert manifest["tables"][0]["primary_key"] == ["id"]
    assert store.verify(workspace_id, manifest["tables"][0]["object"]["key"], manifest["tables"][0]["object"]["sha256"])


@pytest.mark.asyncio
async def test_capture_records_declared_valid_time_bounds_inside_same_snapshot(tmp_path):
    class TemporalConnection(_Connection):
        async def fetchrow(self, query):
            assert 'MIN("valid_from")' in query
            return {
                "valid_from_min": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "valid_from_max": datetime(2025, 1, 31, tzinfo=timezone.utc),
            }

        async def fetch(self, query, schema, table):
            columns = await super().fetch(query, schema, table)
            if "information_schema.columns" in query:
                columns.append({"column_name": "valid_from", "data_type": "timestamp with time zone", "udt_name": "timestamptz", "is_nullable": "YES", "numeric_precision": None, "numeric_scale": None})
            return columns

    connection = TemporalConnection()

    async def connect(_):
        return connection

    workspace, source = uuid4(), uuid4()
    store = LocalSnapshotStore(str(tmp_path))
    capture = PostgresSnapshotCapture(store, CaptureLimits(batch_rows=1, max_rows=10, max_bytes=1_000_000), connect)
    result = await capture.capture("postgresql://example.test/db", workspace, source, [CaptureTable("sales", "orders", valid_from_column="valid_from")])
    manifest = store.read_manifest(workspace, result.manifest_key)
    assert manifest["tables"][0]["valid_time"] == {
        "columns": {"valid_from": "valid_from"},
        "valid_from_min": "2025-01-01T00:00:00+00:00",
        "valid_from_max": "2025-01-31T00:00:00+00:00",
    }


@pytest.mark.asyncio
async def test_capture_rejects_unbounded_numeric_before_writing_objects(tmp_path):
    class UnsupportedConnection(_Connection):
        async def fetch(self, query, schema, table):
            if "information_schema.columns" in query:
                return [{"column_name": "amount", "data_type": "numeric", "udt_name": "numeric", "is_nullable": "YES", "numeric_precision": None, "numeric_scale": None}]
            return []

    connection = UnsupportedConnection()

    async def connect(_):
        return connection

    capture = PostgresSnapshotCapture(LocalSnapshotStore(str(tmp_path)), CaptureLimits(), connect)
    with pytest.raises(SnapshotCaptureError, match="unbounded") as raised:
        await capture.capture("postgresql://example.test/db", uuid4(), uuid4(), [CaptureTable("public", "payments")])
    assert raised.value.category == "unsupported_type"
    assert not list(tmp_path.rglob("*.parquet"))


@pytest.mark.asyncio
async def test_discovery_reports_unsupported_tables_without_reading_table_rows(tmp_path):
    class DiscoveryConnection(_Connection):
        async def fetch(self, query, *args):
            if "information_schema.tables" in query:
                assert args == (2,)
                return [
                    {"table_schema": "sales", "table_name": "orders"},
                    {"table_schema": "sales", "table_name": "events"},
                ]
            schema, table = args
            if "information_schema.columns" in query and table == "events":
                return [{"column_name": "payload", "data_type": "jsonb", "udt_name": "jsonb", "is_nullable": "YES", "numeric_precision": None, "numeric_scale": None}]
            return await super().fetch(query, schema, table)

    connection = DiscoveryConnection()

    async def connect(_):
        return connection

    discovery = PostgresSnapshotCapture(LocalSnapshotStore(str(tmp_path)), CaptureLimits(max_tables=2), connect)
    tables = await discovery.discover_tables("postgresql://example.test/db")

    assert [(item["schema"], item["table"]) for item in tables] == [("sales", "orders"), ("sales", "events")]
    assert tables[0]["capture_supported"] is True
    assert tables[0]["primary_key"] == ["id"]
    assert tables[1]["capture_supported"] is False
    assert "unsupported PostgreSQL type" in tables[1]["unsupported_reason"]


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("METRICTRACE_TEST_POSTGRES_URL"), reason="requires an explicit disposable PostgreSQL URL")
async def test_postgresql_mvcc_snapshot_is_consistent_across_tables(tmp_path):
    """Demonstrate that two tables read through one capture see one MVCC snapshot."""
    import asyncpg
    import pyarrow.parquet as pq

    dsn = os.environ["METRICTRACE_TEST_POSTGRES_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
    schema = f"metrictrace_capture_{uuid4().hex}"
    admin = await asyncpg.connect(dsn)
    writer = await asyncpg.connect(dsn)
    workspace_id, source_id = uuid4(), uuid4()
    changed = False
    try:
        await admin.execute(f'CREATE SCHEMA "{schema}"')
        await admin.execute(f'CREATE TABLE "{schema}".parents (id integer PRIMARY KEY, name text NOT NULL)')
        await admin.execute(f'CREATE TABLE "{schema}".children (id integer PRIMARY KEY, parent_id integer NOT NULL REFERENCES "{schema}".parents(id), amount numeric(12, 2) NOT NULL)')
        await admin.execute(f'INSERT INTO "{schema}".parents VALUES (1, \'before\')')
        await admin.execute(f'INSERT INTO "{schema}".children VALUES (1, 1, 10.00)')

        async def mutate_after_parent(table: CaptureTable) -> None:
            nonlocal changed
            if table.table != "parents" or changed:
                return
            changed = True
            await writer.execute(f"UPDATE \"{schema}\".parents SET name = 'after' WHERE id = 1")
            await writer.execute(f"UPDATE \"{schema}\".children SET amount = 20.00 WHERE id = 1")

        store = LocalSnapshotStore(str(tmp_path))
        capture = PostgresSnapshotCapture(
            store,
            CaptureLimits(batch_rows=1, max_rows=10, max_bytes=1_000_000),
            after_table_captured=mutate_after_parent,
        )
        first = await capture.capture(dsn, workspace_id, source_id, [CaptureTable(schema, "parents"), CaptureTable(schema, "children")])
        manifest = store.read_manifest(workspace_id, first.manifest_key)
        first_values = [pq.read_table(tmp_path / entry["object"]["key"]).to_pylist() for entry in manifest["tables"]]
        assert first_values == [[{"id": 1, "name": "before"}], [{"id": 1, "parent_id": 1, "amount": Decimal("10.00")}]]

        second = await PostgresSnapshotCapture(store, CaptureLimits(batch_rows=1, max_rows=10, max_bytes=1_000_000)).capture(
            dsn, workspace_id, source_id, [CaptureTable(schema, "parents"), CaptureTable(schema, "children")]
        )
        newer = store.read_manifest(workspace_id, second.manifest_key)
        second_values = [pq.read_table(tmp_path / entry["object"]["key"]).to_pylist() for entry in newer["tables"]]
        assert second_values == [[{"id": 1, "name": "after"}], [{"id": 1, "parent_id": 1, "amount": Decimal("20.00")}]]
    finally:
        await admin.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        await writer.close()
        await admin.close()
