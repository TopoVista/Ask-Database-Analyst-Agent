"""Deterministic capture and replay service.

This module intentionally contains no LLM dependency. It is the authority for
historical numbers and produces a durable evidence record for every replay.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.infrastructure.storage import LocalParquetStorage
from app.models.metrictrace import (
    DatasetVersion,
    Metric,
    MetricDefinition,
    MetricObservation,
    MetricSource,
    ReplayCell,
    ReplayJob,
    Workspace,
    WorkspaceMember,
)
from app.models.user import User
from app.tools.sql_validator import validate_sql


class MetricTraceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = LocalParquetStorage(get_settings().historical_storage_dir)

    async def workspace_for_user(self, user: User) -> Workspace:
        result = await self.db.execute(
            select(Workspace).join(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
        )
        workspace = result.scalars().first()
        if workspace:
            return workspace
        workspace = Workspace(name=f"{user.name or user.email}'s workspace")
        self.db.add(workspace)
        await self.db.flush()
        self.db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
        await self.db.flush()
        return workspace

    async def _owned_workspace(self, user: User, workspace_id: UUID) -> Workspace:
        result = await self.db.execute(
            select(Workspace)
            .join(WorkspaceMember)
            .where(Workspace.id == workspace_id, WorkspaceMember.user_id == user.id)
        )
        workspace = result.scalars().first()
        if not workspace:
            raise LookupError("Workspace not found")
        return workspace

    async def capture_records(
        self,
        workspace: Workspace,
        source: MetricSource,
        records: list[dict[str, Any]],
        parent_version_id: UUID | None = None,
    ) -> DatasetVersion:
        version_id, manifest_uri, content_hash, byte_size, schema = self.storage.publish_records(
            workspace.id, source.id, records
        )
        version = DatasetVersion(
            id=version_id,
            source_id=source.id,
            parent_version_id=parent_version_id,
            manifest_uri=manifest_uri,
            content_hash=content_hash,
            row_count=len(records),
            byte_size=byte_size,
            schema_json=schema,
            consistency_level="import",
            status="ready",
        )
        self.db.add(version)
        await self.db.flush()
        return version

    @staticmethod
    def _sql_hash(sql: str) -> str:
        return hashlib.sha256(" ".join(sql.split()).encode("utf-8")).hexdigest()

    async def _execute_cell(self, definition: MetricDefinition, version: DatasetVersion) -> tuple[str, int]:
        validation = validate_sql(definition.sql)
        if not validation.is_valid:
            raise ValueError(validation.reason)
        started = time.perf_counter()
        try:
            import duckdb
        except ImportError as exc:  # pragma: no cover - surfaced in configuration tests
            raise RuntimeError("Historical execution requires duckdb. Install backend requirements.") from exc

        parquet_path = self.storage.parquet_path(version.manifest_uri).as_posix().replace("'", "''")
        connection = duckdb.connect(":memory:")
        try:
            connection.execute(f"CREATE VIEW source_data AS SELECT * FROM read_parquet('{parquet_path}')")
            row = connection.execute(validation.normalized_sql).fetchone()
            if row is None or len(row) != 1 or row[0] is None:
                raise ValueError("Metric SQL must return exactly one non-null scalar value.")
            value = row[0]
            # str preserves Decimal-scale values and keeps API values JSON safe.
            result = str(value)
        finally:
            connection.close()
        return result, round((time.perf_counter() - started) * 1000)

    async def replay(
        self,
        user: User,
        workspace_id: UUID,
        old_version_id: UUID,
        new_version_id: UUID,
        old_definition_id: UUID,
        new_definition_id: UUID,
    ) -> ReplayJob:
        workspace = await self._owned_workspace(user, workspace_id)
        versions = await self.db.execute(
            select(DatasetVersion, MetricSource)
            .join(MetricSource, DatasetVersion.source_id == MetricSource.id)
            .where(DatasetVersion.id.in_([old_version_id, new_version_id]), MetricSource.workspace_id == workspace.id)
        )
        owned_versions = {version.id: version for version, _ in versions.all()}
        if set(owned_versions) != {old_version_id, new_version_id}:
            raise LookupError("One or more dataset versions are unavailable in this workspace")
        definitions = await self.db.execute(
            select(MetricDefinition)
            .join(Metric)
            .where(MetricDefinition.id.in_([old_definition_id, new_definition_id]), Metric.workspace_id == workspace.id)
        )
        owned_definitions = {definition.id: definition for definition in definitions.scalars().all()}
        if set(owned_definitions) != {old_definition_id, new_definition_id}:
            raise LookupError("One or more metric definitions are unavailable in this workspace")

        job = ReplayJob(workspace_id=workspace.id, status="running")
        self.db.add(job)
        await self.db.flush()
        inputs = (
            ("old_data_old_definition", old_definition_id, old_version_id),
            ("old_data_new_definition", new_definition_id, old_version_id),
            ("new_data_old_definition", old_definition_id, new_version_id),
            ("new_data_new_definition", new_definition_id, new_version_id),
        )
        results: dict[str, Decimal] = {}
        for label, definition_id, version_id in inputs:
            definition, version = owned_definitions[definition_id], owned_versions[version_id]
            cell = ReplayCell(
                replay_job_id=job.id,
                label=label,
                definition_id=definition_id,
                dataset_version_id=version_id,
                status="running",
            )
            self.db.add(cell)
            await self.db.flush()
            try:
                result, duration = await self._execute_cell(definition, version)
                cell.result_text, cell.duration_ms, cell.status = result, duration, "completed"
                results[label] = Decimal(result)
                self.db.add(
                    MetricObservation(
                        definition_id=definition_id,
                        dataset_version_id=version_id,
                        result_text=result,
                        status="completed",
                        duration_ms=duration,
                    )
                )
            except Exception as exc:
                cell.status, cell.error = "failed", str(exc)
                job.status = "failed"
        if job.status != "failed":
            old_old = results["old_data_old_definition"]
            old_new = results["old_data_new_definition"]
            new_old = results["new_data_old_definition"]
            new_new = results["new_data_new_definition"]
            job.attribution = {
                "data_effect": str(new_old - old_old),
                "definition_effect": str(old_new - old_old),
                "interaction_effect": str(new_new - new_old - old_new + old_old),
                "total_change": str(new_new - old_old),
                "reconciles": (new_old - old_old) + (old_new - old_old) + (new_new - new_old - old_new + old_old) == new_new - old_old,
            }
            job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return job

    async def demo(self, user: User) -> dict[str, Any]:
        """Create and replay the canonical no-AI metric-regression fixture once."""
        workspace = await self.workspace_for_user(user)
        source_result = await self.db.execute(
            select(MetricSource).where(MetricSource.workspace_id == workspace.id, MetricSource.name == "Monday revenue fixture")
        )
        source = source_result.scalars().first()
        if source is None:
            source = MetricSource(workspace_id=workspace.id, name="Monday revenue fixture", source_type="fixture")
            self.db.add(source)
            await self.db.flush()
            old_records = [
                {"order_id": "a-1", "amount_inr": 1_200_000, "status": "paid", "channel": "direct"},
                {"order_id": "a-2", "amount_inr": 1_200_000, "status": "paid", "channel": "marketplace"},
            ]
            new_records = [
                {"order_id": "a-1", "amount_inr": 1_200_000, "status": "paid", "channel": "direct"},
                {"order_id": "a-2", "amount_inr": 600_000, "status": "paid", "channel": "marketplace"},
            ]
            old_version = await self.capture_records(workspace, source, old_records)
            new_version = await self.capture_records(workspace, source, new_records, old_version.id)
            metric = Metric(workspace_id=workspace.id, name="Monday revenue", description="Paid order revenue in INR")
            self.db.add(metric)
            await self.db.flush()
            original_sql = "SELECT SUM(amount_inr) FROM source_data WHERE status = 'paid'"
            proposed_sql = "SELECT SUM(amount_inr) FROM source_data WHERE status = 'paid' AND channel <> 'marketplace'"
            old_definition = MetricDefinition(metric_id=metric.id, version=1, sql=original_sql, normalized_sql_hash=self._sql_hash(original_sql), unit="INR", currency="INR")
            new_definition = MetricDefinition(metric_id=metric.id, version=2, sql=proposed_sql, normalized_sql_hash=self._sql_hash(proposed_sql), unit="INR", currency="INR")
            self.db.add_all([old_definition, new_definition])
            await self.db.flush()
        else:
            versions = await self.db.execute(select(DatasetVersion).where(DatasetVersion.source_id == source.id).order_by(DatasetVersion.captured_at))
            ordered_versions = list(versions.scalars().all())
            metric_result = await self.db.execute(select(Metric).where(Metric.workspace_id == workspace.id, Metric.name == "Monday revenue"))
            metric = metric_result.scalars().one()
            definitions = await self.db.execute(select(MetricDefinition).where(MetricDefinition.metric_id == metric.id).order_by(MetricDefinition.version))
            ordered_definitions = list(definitions.scalars().all())
            old_version, new_version = ordered_versions[0], ordered_versions[-1]
            old_definition, new_definition = ordered_definitions[0], ordered_definitions[-1]

        job = await self.replay(user, workspace.id, old_version.id, new_version.id, old_definition.id, new_definition.id)
        cells = await self.db.execute(select(ReplayCell).where(ReplayCell.replay_job_id == job.id).order_by(ReplayCell.label))
        return {
            "workspace_id": str(workspace.id),
            "replay_id": str(job.id),
            "status": job.status,
            "headline": "Monday revenue was ₹24 lakh at capture, then ₹18 lakh on corrected data using the original definition.",
            "inputs": {
                "old_dataset_version": str(old_version.id), "new_dataset_version": str(new_version.id),
                "old_definition": str(old_definition.id), "new_definition": str(new_definition.id),
            },
            "cells": [
                {"label": cell.label, "result_inr": cell.result_text, "status": cell.status, "error": cell.error}
                for cell in cells.scalars().all()
            ],
            "attribution": job.attribution,
        }
