"""Bounded, repeatable-read PostgreSQL capture into immutable Parquet objects.

The adapter has no SQLAlchemy dependency.  It owns a *short-lived source
connection* and establishes one PostgreSQL MVCC snapshot before inspecting or
reading any selected table.  It is intentionally conservative: unsupported
source types fail the complete attempt instead of producing a misleading,
partly typed historical snapshot.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import UUID

from app.infrastructure.storage.snapshot_store import SnapshotStore


@dataclass(frozen=True)
class CaptureTable:
    schema: str
    table: str
    valid_from_column: str | None = None
    valid_to_column: str | None = None

    def __post_init__(self) -> None:
        names = [self.schema, self.table, self.valid_from_column or "", self.valid_to_column or ""]
        if not self.schema or not self.table or "\x00" in "".join(names):
            raise ValueError("A PostgreSQL table must have non-empty schema and table names.")

    @property
    def identity(self) -> str:
        return f"{self.schema}.{self.table}"


@dataclass(frozen=True)
class CaptureLimits:
    batch_rows: int = 2_000
    max_tables: int = 16
    max_rows: int = 5_000_000
    max_bytes: int = 2 * 1024 * 1024 * 1024
    timeout_seconds: int = 900

    def __post_init__(self) -> None:
        if min(self.batch_rows, self.max_tables, self.max_rows, self.max_bytes, self.timeout_seconds) < 1:
            raise ValueError("Capture limits must be positive.")


class SnapshotCaptureError(RuntimeError):
    """Stable capture error with a machine-readable category."""

    def __init__(self, category: str, message: str):
        self.category = category
        super().__init__(message)

    def as_dict(self) -> dict[str, str]:
        return {"category": self.category, "message": str(self)}


@dataclass(frozen=True)
class CapturedSnapshot:
    attempt_id: UUID
    manifest_key: str
    content_hash: str
    row_count: int
    byte_size: int
    schema: dict[str, Any]
    source_snapshot_at: datetime | None


_TYPE_MAP = {
    "bool": "boolean",
    "int2": "smallint",
    "int4": "integer",
    "int8": "bigint",
    "float4": "real",
    "float8": "double precision",
    "text": "text",
    "varchar": "character varying",
    "bpchar": "character",
    "date": "date",
    "timestamp": "timestamp without time zone",
    "timestamptz": "timestamp with time zone",
}


def _quote_identifier(identifier: str) -> str:
    # Parameters cannot represent SQL identifiers. PostgreSQL's quoted
    # identifier grammar is safe when quotes are escaped this way.
    return '"' + identifier.replace('"', '""') + '"'


def _driver_dsn(connection_string: str) -> str:
    return connection_string.replace("postgresql+asyncpg://", "postgresql://", 1)


class PostgresSnapshotCapture:
    """Captures selected PostgreSQL tables under one explicit MVCC snapshot."""

    def __init__(
        self,
        store: SnapshotStore,
        limits: CaptureLimits,
        connect: Callable[[str], Awaitable[Any]] | None = None,
        after_table_captured: Callable[[CaptureTable], Awaitable[None]] | None = None,
    ) -> None:
        self.store = store
        self.limits = limits
        self._connect = connect
        self._after_table_captured = after_table_captured

    async def capture(
        self,
        connection_string: str,
        workspace_id: UUID,
        source_id: UUID,
        tables: list[CaptureTable],
    ) -> CapturedSnapshot:
        self._validate_tables(tables)
        connect = self._connect or self._asyncpg_connect
        attempt_id = uuid.uuid4()
        # Keep local keys compact enough for Windows development paths. The
        # manifest records the source ID; workspace + unique attempt ID is the
        # immutable object identity needed by storage.
        prefix = f"workspaces/{workspace_id}/a/{attempt_id}"
        connection = None
        started = time.monotonic()
        try:
            connection = await connect(_driver_dsn(connection_string))
            transaction = connection.transaction(isolation="repeatable_read", readonly=True)
            await transaction.start()
            # This first statement fixes the PostgreSQL transaction snapshot
            # before catalog discovery or any table cursor begins.
            snapshot_id = await connection.fetchval("SELECT txid_current_snapshot()")
            source_snapshot_at = await connection.fetchval("SELECT CURRENT_TIMESTAMP")
            await connection.execute("SELECT set_config('statement_timeout', $1, true)", str(self.limits.timeout_seconds * 1000))
            table_manifests: list[dict[str, Any]] = []
            total_rows = total_bytes = 0
            with tempfile.TemporaryDirectory(prefix="metrictrace-capture-") as raw_temp:
                temp_dir = Path(raw_temp)
                for index, selected in enumerate(tables):
                    self._ensure_deadline(started)
                    metadata = await self._table_metadata(connection, selected)
                    temporal_bounds = await self._temporal_bounds(connection, selected, metadata["columns"])
                    local_path, row_count, arrow_schema = await self._stream_table(
                        connection, selected, metadata["columns"], temp_dir / f"{index}.parquet", started
                    )
                    object_key = f"{prefix}/tables/{index}.parquet"
                    object_metadata = self.store.put_file(workspace_id, object_key, local_path)
                    if not self.store.verify(workspace_id, object_key, object_metadata.sha256):
                        raise SnapshotCaptureError("storage_verification_failed", f"Uploaded object could not be verified: {selected.identity}")
                    total_rows += row_count
                    total_bytes += object_metadata.size_bytes
                    self._ensure_limits(total_rows, total_bytes)
                    table_manifests.append({
                        "schema": selected.schema,
                        "table": selected.table,
                        "primary_key": metadata["primary_key"],
                        "foreign_keys": metadata["foreign_keys"],
                        "columns": metadata["columns"],
                        "arrow_schema": str(arrow_schema),
                        "object": {"key": object_key, "sha256": object_metadata.sha256, "bytes": object_metadata.size_bytes},
                        "row_count": row_count,
                        "valid_time": temporal_bounds,
                    })
                    if self._after_table_captured is not None:
                        await self._after_table_captured(selected)
                manifest = {
                    "format_version": 2,
                    "consistency_level": "postgresql_repeatable_read",
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "source_snapshot": str(snapshot_id),
                    "source_snapshot_at": self._timestamp(source_snapshot_at),
                    "source_id": str(source_id),
                    "attempt_id": str(attempt_id),
                    "row_count": total_rows,
                    "byte_size": total_bytes,
                    "tables": table_manifests,
                }
                body = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
                content_hash = hashlib.sha256(body).hexdigest()
                manifest_key = f"{prefix}/manifest.json"
                manifest_object = self.store.put(workspace_id, manifest_key, body)
                if not self.store.verify(workspace_id, manifest_key, manifest_object.sha256):
                    raise SnapshotCaptureError("storage_verification_failed", "Uploaded manifest could not be verified.")
            await transaction.commit()
            return CapturedSnapshot(
                attempt_id=attempt_id,
                manifest_key=manifest_key,
                content_hash=content_hash,
                row_count=total_rows,
                byte_size=total_bytes,
                schema={"tables": table_manifests},
                source_snapshot_at=source_snapshot_at if isinstance(source_snapshot_at, datetime) else None,
            )
        except SnapshotCaptureError:
            if connection is not None:
                await self._safe_rollback(connection)
            self._cleanup_staging(workspace_id, prefix)
            raise
        except asyncio.TimeoutError as exc:
            if connection is not None:
                await self._safe_rollback(connection)
            self._cleanup_staging(workspace_id, prefix)
            raise SnapshotCaptureError("capture_timeout", "The capture exceeded its configured duration.") from exc
        except Exception as exc:
            if connection is not None:
                await self._safe_rollback(connection)
            self._cleanup_staging(workspace_id, prefix)
            raise SnapshotCaptureError("source_or_storage_error", str(exc)) from exc
        finally:
            if connection is not None:
                await connection.close()

    async def discover_tables(self, connection_string: str) -> list[dict[str, Any]]:
        """Return a bounded catalog view without reading table data.

        Discovery deliberately uses the same type validation as capture.  A
        table with an unsupported capture type is disclosed as unavailable,
        rather than allowing it to be selected and failing after an expensive
        source read has begun.
        """
        connect = self._connect or self._asyncpg_connect
        connection = None
        try:
            connection = await connect(_driver_dsn(connection_string))
            transaction = connection.transaction(readonly=True)
            await transaction.start()
            table_rows = await connection.fetch(
                """SELECT table_schema, table_name
                   FROM information_schema.tables
                   WHERE table_type = 'BASE TABLE'
                     AND table_schema NOT IN ('pg_catalog', 'information_schema')
                   ORDER BY table_schema, table_name
                   LIMIT $1""",
                self.limits.max_tables,
            )
            discovered: list[dict[str, Any]] = []
            for row in table_rows:
                table = CaptureTable(schema=row["table_schema"], table=row["table_name"])
                try:
                    metadata = await self._table_metadata(connection, table)
                    discovered.append({
                        "schema": table.schema,
                        "table": table.table,
                        "primary_key": metadata["primary_key"],
                        "columns": metadata["columns"],
                        "capture_supported": True,
                        "unsupported_reason": None,
                    })
                except SnapshotCaptureError as exc:
                    discovered.append({
                        "schema": table.schema,
                        "table": table.table,
                        "primary_key": [],
                        "columns": [],
                        "capture_supported": False,
                        "unsupported_reason": str(exc),
                    })
            await transaction.commit()
            return discovered
        except SnapshotCaptureError:
            if connection is not None:
                await self._safe_rollback(connection)
            raise
        except Exception as exc:
            if connection is not None:
                await self._safe_rollback(connection)
            raise SnapshotCaptureError("catalog_discovery_failed", str(exc)) from exc
        finally:
            if connection is not None:
                await connection.close()

    async def _asyncpg_connect(self, dsn: str) -> Any:
        try:
            import asyncpg
        except ImportError as exc:  # pragma: no cover - deployment configuration
            raise SnapshotCaptureError("dependency_missing", "PostgreSQL capture requires asyncpg.") from exc
        return await asyncpg.connect(dsn)

    def _validate_tables(self, tables: list[CaptureTable]) -> None:
        if not tables:
            raise SnapshotCaptureError("invalid_configuration", "At least one source table must be selected.")
        if len(tables) > self.limits.max_tables:
            raise SnapshotCaptureError("limit_exceeded", f"A capture may select at most {self.limits.max_tables} tables.")
        if len({table.identity for table in tables}) != len(tables):
            raise SnapshotCaptureError("invalid_configuration", "A table may be selected only once per capture.")

    async def _table_metadata(self, connection: Any, table: CaptureTable) -> dict[str, Any]:
        columns = [dict(row) for row in await connection.fetch(
            """SELECT column_name, data_type, udt_name, is_nullable, numeric_precision, numeric_scale
               FROM information_schema.columns
               WHERE table_schema = $1 AND table_name = $2 ORDER BY ordinal_position""",
            table.schema, table.table,
        )]
        if not columns:
            raise SnapshotCaptureError("table_not_found_or_forbidden", f"No readable columns found for {table.identity}.")
        self._arrow_schema(columns)  # Validate before creating any object.
        primary_key = [row["column_name"] for row in await connection.fetch(
            """SELECT kcu.column_name
               FROM information_schema.table_constraints tc
               JOIN information_schema.key_column_usage kcu
                 ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
               WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = $1 AND tc.table_name = $2
               ORDER BY kcu.ordinal_position""",
            table.schema, table.table,
        )]
        foreign_keys = [dict(row) for row in await connection.fetch(
            """SELECT kcu.column_name, ccu.table_schema AS foreign_table_schema,
                      ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
               FROM information_schema.table_constraints tc
               JOIN information_schema.key_column_usage kcu
                 ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
               JOIN information_schema.constraint_column_usage ccu
                 ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
               WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = $1 AND tc.table_name = $2
               ORDER BY kcu.ordinal_position""",
            table.schema, table.table,
        )]
        return {"columns": columns, "primary_key": primary_key, "foreign_keys": foreign_keys}

    async def _temporal_bounds(self, connection: Any, table: CaptureTable, columns: list[dict[str, Any]]) -> dict[str, Any] | None:
        configured = [("valid_from", table.valid_from_column), ("valid_to", table.valid_to_column)]
        configured = [(label, name) for label, name in configured if name]
        if not configured:
            return None
        types = {str(column["column_name"]): str(column["data_type"]) for column in columns}
        allowed = {"date", "timestamp without time zone", "timestamp with time zone"}
        for _, name in configured:
            if name not in types or types[name] not in allowed:
                raise SnapshotCaptureError("invalid_valid_time", f"{table.identity} valid-time column {name!r} must be a captured date/timestamp column.")
        expressions = ", ".join(
            f"MIN({_quote_identifier(name)}) AS {label}_min, MAX({_quote_identifier(name)}) AS {label}_max"
            for label, name in configured
        )
        row = await connection.fetchrow(f"SELECT {expressions} FROM {_quote_identifier(table.schema)}.{_quote_identifier(table.table)}")
        result = {"columns": {label: name for label, name in configured}}
        for label, _ in configured:
            result[f"{label}_min"] = self._timestamp(row.get(f"{label}_min")) if row else None
            result[f"{label}_max"] = self._timestamp(row.get(f"{label}_max")) if row else None
        return result

    @staticmethod
    def _timestamp(value: Any) -> str | None:
        return value.isoformat() if isinstance(value, (datetime,)) else (value.isoformat() if hasattr(value, "isoformat") else None)

    async def _stream_table(self, connection: Any, table: CaptureTable, columns: list[dict[str, Any]], path: Path, started: float) -> tuple[Path, int, Any]:
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as exc:  # pragma: no cover - deployment configuration
            raise SnapshotCaptureError("dependency_missing", "PostgreSQL capture requires pyarrow.") from exc
        schema = self._arrow_schema(columns)
        query = f"SELECT * FROM {_quote_identifier(table.schema)}.{_quote_identifier(table.table)}"
        row_count = 0
        writer = pq.ParquetWriter(path, schema, compression="zstd")
        try:
            batch: list[dict[str, Any]] = []
            async for record in connection.cursor(query, prefetch=self.limits.batch_rows):
                batch.append(dict(record))
                if len(batch) >= self.limits.batch_rows:
                    writer.write_table(self._to_arrow_table(pa, batch, schema, table))
                    row_count += len(batch)
                    self._ensure_limits(row_count, path.stat().st_size)
                    self._ensure_deadline(started)
                    batch = []
            if batch:
                writer.write_table(self._to_arrow_table(pa, batch, schema, table))
                row_count += len(batch)
                self._ensure_limits(row_count, path.stat().st_size)
            self._ensure_deadline(started)
        finally:
            writer.close()
        return path, row_count, schema

    @staticmethod
    def _to_arrow_table(pa: Any, records: list[dict[str, Any]], schema: Any, table: CaptureTable) -> Any:
        try:
            return pa.Table.from_pylist(records, schema=schema)
        except (pa.ArrowInvalid, pa.ArrowTypeError, ValueError) as exc:
            raise SnapshotCaptureError("unsupported_value", f"{table.identity} has a value incompatible with its captured schema: {exc}") from exc

    @staticmethod
    def _arrow_schema(columns: list[dict[str, Any]]) -> Any:
        try:
            import pyarrow as pa
        except ImportError as exc:  # pragma: no cover
            raise SnapshotCaptureError("dependency_missing", "PostgreSQL capture requires pyarrow.") from exc
        fields = []
        for column in columns:
            data_type = _TYPE_MAP.get(column["udt_name"], column["data_type"])
            name = column["column_name"]
            if data_type == "boolean":
                arrow_type = pa.bool_()
            elif data_type == "smallint":
                arrow_type = pa.int16()
            elif data_type == "integer":
                arrow_type = pa.int32()
            elif data_type == "bigint":
                arrow_type = pa.int64()
            elif data_type == "real":
                arrow_type = pa.float32()
            elif data_type == "double precision":
                arrow_type = pa.float64()
            elif data_type in {"text", "character varying", "character"}:
                arrow_type = pa.string()
            elif data_type == "date":
                arrow_type = pa.date32()
            elif data_type == "timestamp without time zone":
                arrow_type = pa.timestamp("us")
            elif data_type == "timestamp with time zone":
                arrow_type = pa.timestamp("us", tz="UTC")
            elif data_type in {"numeric", "decimal"}:
                precision, scale = column.get("numeric_precision"), column.get("numeric_scale")
                if precision is None or scale is None or precision > 38 or scale < 0:
                    raise SnapshotCaptureError("unsupported_type", f"{name} uses unbounded or unsupported NUMERIC precision.")
                arrow_type = pa.decimal128(precision, scale)
            else:
                raise SnapshotCaptureError("unsupported_type", f"{name} has unsupported PostgreSQL type {data_type!r}.")
            fields.append(pa.field(name, arrow_type, nullable=column["is_nullable"] == "YES"))
        return pa.schema(fields)

    def _ensure_limits(self, rows: int, bytes_written: int) -> None:
        if rows > self.limits.max_rows:
            raise SnapshotCaptureError("row_limit_exceeded", f"Capture exceeds {self.limits.max_rows} rows.")
        if bytes_written > self.limits.max_bytes:
            raise SnapshotCaptureError("byte_limit_exceeded", f"Capture exceeds {self.limits.max_bytes} bytes.")

    def _ensure_deadline(self, started: float) -> None:
        if time.monotonic() - started > self.limits.timeout_seconds:
            raise SnapshotCaptureError("capture_timeout", "The capture exceeded its configured duration.")

    async def _safe_rollback(self, connection: Any) -> None:
        try:
            await connection.execute("ROLLBACK")
        except Exception:
            pass

    def _cleanup_staging(self, workspace_id: UUID, prefix: str) -> None:
        # Capture objects use final, unique attempt identities so storage never
        # overwrites an authoritative object.  A failed attempt may therefore
        # leave an unreferenced orphan; it must be reconciled by a metadata
        # aware retention job, never by a broad prefix delete that could race a
        # successful metadata publication.
        del workspace_id, prefix
