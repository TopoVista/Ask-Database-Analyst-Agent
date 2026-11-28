"""Deterministic capture and replay service.

This module intentionally contains no LLM dependency. It is the authority for
historical numbers and produces a durable evidence record for every replay.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domain.attribution import four_way_attribution
from app.infrastructure.capture import CaptureLimits, CaptureTable, PostgresSnapshotCapture
from app.infrastructure.storage import LocalParquetStorage
from app.infrastructure.storage.snapshot_store import snapshot_store_from_settings
from app.services.connection_service import ConnectionService
from app.models.metrictrace import (
    ContractEvaluation,
    DatasetVersion,
    DurableJob,
    Metric,
    MetricContract,
    MetricDefinition,
    MetricObservation,
    MetricPromotion,
    MetricSource,
    ReplayCell,
    ReplayJob,
    RegressionPolicy,
    ShadowExecution,
    Workspace,
    WorkspaceMember,
)
from app.models.connection import DBConnection
from app.services.job_queue import DurableJobQueue
from app.models.user import User
from app.tools.sql_validator import validate_sql
from metrictrace_sdk.lineage import inspect_sql_lineage
from metrictrace_sdk.dataset_diff import DatasetDiffError, compare_datasets
from metrictrace_sdk.regression import check_sql_regression, validate_regression_thresholds
from metrictrace_sdk.join_audit import JoinAuditError, audit_sql_joins
from metrictrace_sdk.contracts import ContractError, ERROR, PASS, evaluate_contracts


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

    async def inspect_static_lineage(
        self, user: User, workspace_id: UUID, sql: str, allowed_tables: list[str]
    ) -> dict[str, Any]:
        """Run shared static analysis only after tenant-scoped workspace authorization.

        The request contains SQL text and a declared logical allow-list only;
        it neither reads datasets nor discloses other workspace metadata.
        """
        await self._owned_workspace(user, workspace_id)
        return inspect_sql_lineage(sql, allowed_tables)

    async def cleanup_stale_snapshot_attempts(
        self, workspace_id: UUID, retention_seconds: int
    ) -> dict[str, int]:
        """Remove only old, unreferenced capture attempts in one workspace.

        This is intentionally a maintenance primitive, not a public endpoint:
        callers must schedule it under their own operational authorization.
        """
        if retention_seconds < 60:
            raise ValueError("Snapshot attempt retention must be at least 60 seconds.")
        store = snapshot_store_from_settings(get_settings())
        referenced = {
            version.manifest_uri.rsplit("/", 1)[0]
            for version in (await self.db.execute(
                select(DatasetVersion).join(MetricSource).where(MetricSource.workspace_id == workspace_id)
            )).scalars()
        }
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=retention_seconds)
        deleted = retained = 0
        for attempt in store.list_attempts(workspace_id):
            if attempt.prefix in referenced or attempt.modified_at > cutoff:
                retained += 1
                continue
            store.delete_attempt(workspace_id, attempt.prefix)
            deleted += 1
        return {"deleted_attempts": deleted, "retained_attempts": retained}

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

    async def create_postgres_source(
        self,
        user: User,
        workspace_id: UUID,
        connection_id: UUID,
        name: str,
        tables: list[CaptureTable],
        schedule_seconds: int | None = None,
    ) -> MetricSource:
        """Register a source without copying its credentials into MetricTrace metadata."""
        workspace = await self._owned_workspace(user, workspace_id)
        connection = await ConnectionService(self.db).get_connection(connection_id, user.id)
        if connection is None or connection.db_type.lower() not in {"postgres", "postgresql"}:
            raise LookupError("A readable PostgreSQL connection is required.")
        if not tables:
            raise ValueError("At least one table must be selected.")
        source = MetricSource(
            workspace_id=workspace.id,
            connection_id=connection.id,
            name=name,
            source_type="postgresql",
            capture_config={
                "tables": [{"schema": table.schema, "table": table.table} for table in tables],
                "schedule_seconds": schedule_seconds,
            },
            capture_status="ready",
            capabilities={"consistent_snapshot": "postgresql_repeatable_read"},
        )
        self.db.add(source)
        await self.db.flush()
        return source

    async def discover_postgres_tables(
        self, user: User, workspace_id: UUID, connection_id: UUID
    ) -> list[dict[str, Any]]:
        """Discover capture-compatible tables for an owned PostgreSQL connection.

        The decrypted DSN stays inside the service and is never persisted in a
        job payload or returned to the caller.
        """
        await self._owned_workspace(user, workspace_id)
        connection = await ConnectionService(self.db).get_connection(connection_id, user.id)
        if connection is None or connection.db_type.lower() not in {"postgres", "postgresql"}:
            raise LookupError("A readable PostgreSQL connection is required.")
        settings = get_settings()
        limits = CaptureLimits(
            batch_rows=settings.metrictrace_capture_batch_rows,
            max_tables=settings.metrictrace_capture_max_tables,
            max_rows=settings.metrictrace_capture_max_rows,
            max_bytes=settings.metrictrace_capture_max_bytes,
            timeout_seconds=settings.metrictrace_capture_timeout_seconds,
        )
        capture = PostgresSnapshotCapture(snapshot_store_from_settings(settings), limits)
        return await capture.discover_tables(ConnectionService(self.db).build_connection_string(connection))

    async def sources_for_user(self, user: User, workspace_id: UUID) -> list[dict[str, Any]]:
        """List source metadata and capture history without disclosing credentials."""
        await self._owned_workspace(user, workspace_id)
        sources = list(
            (
                await self.db.execute(
                    select(MetricSource)
                    .where(MetricSource.workspace_id == workspace_id)
                    .order_by(MetricSource.created_at.desc())
                )
            ).scalars()
        )
        if not sources:
            return []
        source_ids = [source.id for source in sources]
        versions = list(
            (
                await self.db.execute(
                    select(DatasetVersion)
                    .where(DatasetVersion.source_id.in_(source_ids), DatasetVersion.status == "ready")
                    .order_by(DatasetVersion.captured_at.desc())
                )
            ).scalars()
        )
        by_source: dict[UUID, list[DatasetVersion]] = {source_id: [] for source_id in source_ids}
        for version in versions:
            by_source[version.source_id].append(version)
        return [
            {
                "id": str(source.id),
                "name": source.name,
                "source_type": source.source_type,
                "connection_id": str(source.connection_id) if source.connection_id else None,
                "capture_status": source.capture_status,
                "tables": source.capture_config.get("tables", []),
                "schedule_seconds": source.capture_config.get("schedule_seconds"),
                "version_count": len(by_source[source.id]),
                "latest_version_id": str(by_source[source.id][0].id) if by_source[source.id] else None,
                "latest_captured_at": by_source[source.id][0].captured_at.isoformat() if by_source[source.id] else None,
            }
            for source in sources
        ]

    async def compare_dataset_versions(
        self,
        user: User,
        workspace_id: UUID,
        old_version_id: UUID,
        new_version_id: UUID,
        key_columns: list[str],
        *,
        old_table: CaptureTable | None = None,
        new_table: CaptureTable | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Run the shared Dataset Diff engine over two owned immutable versions.

        API callers provide version IDs and optional catalog table identities,
        never a local path or storage key.  Multi-table PostgreSQL snapshots
        require explicit table selections so data from unrelated tables cannot
        be compared accidentally.
        """
        workspace = await self._owned_workspace(user, workspace_id)
        versions = await self.db.execute(
            select(DatasetVersion, MetricSource)
            .join(MetricSource, DatasetVersion.source_id == MetricSource.id)
            .where(
                DatasetVersion.id.in_([old_version_id, new_version_id]),
                DatasetVersion.status == "ready",
                MetricSource.workspace_id == workspace.id,
            )
        )
        owned_versions = {version.id: version for version, _ in versions.all()}
        if set(owned_versions) != {old_version_id, new_version_id}:
            raise LookupError("One or more dataset versions are unavailable in this workspace")

        settings = get_settings()
        store = snapshot_store_from_settings(settings)
        with tempfile.TemporaryDirectory(prefix="metrictrace-diff-") as raw_temp:
            temp_dir = Path(raw_temp)
            old_path, old_identity = self._materialize_diff_object(
                store, workspace.id, owned_versions[old_version_id], old_table, temp_dir, "old"
            )
            # If the caller selected only one capture table, compare the same
            # table identity in the newer snapshot by default.
            effective_new_table = new_table or old_table
            new_path, new_identity = self._materialize_diff_object(
                store, workspace.id, owned_versions[new_version_id], effective_new_table, temp_dir, "new"
            )
            report = compare_datasets(
                str(old_path),
                str(new_path),
                key_columns=key_columns,
                limit=limit,
                offset=offset,
                allowed_roots=(str(temp_dir),),
            )
        return {
            "old_version_id": str(old_version_id),
            "new_version_id": str(new_version_id),
            "old_table": old_identity,
            "new_table": new_identity,
            "comparison": report,
        }

    async def check_sql_regression_for_version(
        self,
        user: User,
        workspace_id: UUID,
        dataset_version_id: UUID,
        baseline_sql: str,
        candidate_sql: str,
        *,
        table: CaptureTable | None = None,
        max_absolute_difference: str | None = None,
        max_percent_difference: str | None = None,
        parameters: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        """Run the shared SQL regression engine against one owned snapshot."""
        workspace = await self._owned_workspace(user, workspace_id)
        version_result = await self.db.execute(
            select(DatasetVersion)
            .join(MetricSource, DatasetVersion.source_id == MetricSource.id)
            .where(
                DatasetVersion.id == dataset_version_id,
                DatasetVersion.status == "ready",
                MetricSource.workspace_id == workspace.id,
            )
        )
        version = version_result.scalars().first()
        if version is None:
            raise LookupError("Dataset version is unavailable in this workspace")
        store = snapshot_store_from_settings(get_settings())
        with tempfile.TemporaryDirectory(prefix="metrictrace-regression-") as raw_temp:
            temp_dir = Path(raw_temp)
            dataset_path, table_identity = self._materialize_diff_object(
                store, workspace.id, version, table, temp_dir, "dataset"
            )
            report = check_sql_regression(
                str(dataset_path),
                baseline_sql,
                candidate_sql,
                max_absolute_difference=max_absolute_difference,
                max_percent_difference=max_percent_difference,
                parameters=parameters,
                allowed_roots=(str(temp_dir),),
            )
        return {
            "dataset_version_id": str(dataset_version_id),
            "table": table_identity,
            "regression": report,
        }

    async def audit_sql_joins_for_version(
        self, user: User, workspace_id: UUID, dataset_version_id: UUID, sql: str
    ) -> dict[str, Any]:
        """Profile supported joins over one tenant-owned immutable snapshot."""
        workspace = await self._owned_workspace(user, workspace_id)
        version_result = await self.db.execute(
            select(DatasetVersion)
            .join(MetricSource, DatasetVersion.source_id == MetricSource.id)
            .where(
                DatasetVersion.id == dataset_version_id,
                DatasetVersion.status == "ready",
                MetricSource.workspace_id == workspace.id,
            )
        )
        version = version_result.scalars().first()
        if version is None:
            raise LookupError("Dataset version is unavailable in this workspace")
        store = snapshot_store_from_settings(get_settings())
        with tempfile.TemporaryDirectory(prefix="metrictrace-join-audit-") as raw_temp:
            temp_dir = Path(raw_temp)
            datasets, table_identities = self._materialize_join_objects(store, workspace.id, version, temp_dir)
            report = audit_sql_joins(datasets, sql, allowed_roots=(str(temp_dir),))
        return {
            "dataset_version_id": str(dataset_version_id),
            "tables": table_identities,
            "audit": report,
        }

    async def create_contract(
        self, user: User, workspace_id: UUID, name: str, contracts: list[dict[str, Any]]
    ) -> MetricContract:
        """Create a new immutable definition version for a tenant-owned contract."""
        workspace = await self._owned_workspace(user, workspace_id)
        if not contracts or any(not isinstance(contract, dict) for contract in contracts):
            raise ContractError("A contract definition must contain one or more objects.")
        canonical = json.dumps(contracts, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        next_version = (
            await self.db.execute(
                select(func.max(MetricContract.version)).where(
                    MetricContract.workspace_id == workspace.id, MetricContract.name == name
                )
            )
        ).scalar_one_or_none()
        contract = MetricContract(
            workspace_id=workspace.id,
            name=name,
            version=(next_version or 0) + 1,
            contracts=json.loads(canonical),
            definition_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        )
        self.db.add(contract)
        await self.db.flush()
        return contract

    async def contracts_for_user(self, user: User, workspace_id: UUID) -> list[dict[str, Any]]:
        """List exact definition versions and their most recent durable evaluation."""
        await self._owned_workspace(user, workspace_id)
        contracts = list(
            (
                await self.db.execute(
                    select(MetricContract)
                    .where(MetricContract.workspace_id == workspace_id)
                    .order_by(MetricContract.name, MetricContract.version.desc())
                )
            ).scalars()
        )
        if not contracts:
            return []
        latest_rows = list(
            (
                await self.db.execute(
                    select(ContractEvaluation)
                    .where(ContractEvaluation.contract_id.in_([contract.id for contract in contracts]))
                    .order_by(ContractEvaluation.created_at.desc())
                )
            ).scalars()
        )
        latest: dict[UUID, ContractEvaluation] = {}
        for evaluation in latest_rows:
            latest.setdefault(evaluation.contract_id, evaluation)
        return [
            self._contract_read(contract, latest.get(contract.id))
            for contract in contracts
        ]

    async def evaluate_contract_for_version(
        self, user: User, workspace_id: UUID, contract_id: UUID, dataset_version_id: UUID
    ) -> dict[str, Any]:
        """Persist shared-engine evaluation evidence for one authorized snapshot."""
        workspace = await self._owned_workspace(user, workspace_id)
        contract = await self.db.get(MetricContract, contract_id)
        if contract is None or contract.workspace_id != workspace.id:
            raise LookupError("Contract definition is unavailable in this workspace")
        version = (
            await self.db.execute(
                select(DatasetVersion)
                .join(MetricSource, DatasetVersion.source_id == MetricSource.id)
                .where(
                    DatasetVersion.id == dataset_version_id,
                    DatasetVersion.status == "ready",
                    MetricSource.workspace_id == workspace.id,
                )
            )
        ).scalars().first()
        if version is None:
            raise LookupError("Dataset version is unavailable in this workspace")
        store = snapshot_store_from_settings(get_settings())
        try:
            with tempfile.TemporaryDirectory(prefix="metrictrace-contract-") as raw_temp:
                temp_dir = Path(raw_temp)
                datasets, table_identities = self._materialize_join_objects(store, workspace.id, version, temp_dir)
                report = evaluate_contracts(datasets, contract.contracts, allowed_roots=(str(temp_dir),))
        except JoinAuditError as exc:
            raise ContractError(str(exc)) from exc
        mandatory_errors = any(
            outcome["severity"] == "error" and outcome["status"] == ERROR
            for outcome in report["outcomes"]
        )
        evaluation_status = PASS if report["summary"]["mandatory_passed"] else (ERROR if mandatory_errors else "FAIL")
        input_fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "contract_hash": contract.definition_hash,
                    "dataset_content_hash": version.content_hash,
                    "outcomes": report["outcomes"],
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        evidence = {
            "format_version": 1,
            "dataset_version_id": str(version.id),
            "dataset_content_hash": version.content_hash,
            "tables": table_identities,
            "report": report,
        }
        evaluation = ContractEvaluation(
            workspace_id=workspace.id,
            contract_id=contract.id,
            dataset_version_id=version.id,
            status=evaluation_status,
            input_fingerprint=input_fingerprint,
            report=evidence,
        )
        self.db.add(evaluation)
        await self.db.flush()
        return {"contract": self._contract_read(contract), "evaluation": self._evaluation_read(evaluation)}

    async def create_regression_policy(
        self, user: User, workspace_id: UUID, name: str, max_absolute_difference: str | None,
        max_percent_difference: str | None, required_contract_id: UUID | None,
    ) -> RegressionPolicy:
        """Version a gate policy before it can approve any shadow execution."""
        workspace = await self._owned_workspace(user, workspace_id)
        if max_absolute_difference is None and max_percent_difference is None:
            raise ValueError("A regression policy requires an absolute or percentage gate.")
        contract = None
        if required_contract_id:
            contract = await self.db.get(MetricContract, required_contract_id)
            if contract is None or contract.workspace_id != workspace.id:
                raise LookupError("Required contract is unavailable in this workspace")
        # Reuse the shared parser so invalid numeric gate values fail before persistence.
        validate_regression_thresholds(max_absolute_difference, max_percent_difference)
        version = (
            await self.db.execute(select(func.max(RegressionPolicy.version)).where(
                RegressionPolicy.workspace_id == workspace.id, RegressionPolicy.name == name
            ))
        ).scalar_one_or_none()
        canonical = {"absolute": max_absolute_difference, "percent": max_percent_difference, "contract": str(required_contract_id) if required_contract_id else None}
        policy = RegressionPolicy(
            workspace_id=workspace.id, name=name, version=(version or 0) + 1,
            max_absolute_difference=max_absolute_difference, max_percent_difference=max_percent_difference,
            required_contract_id=required_contract_id,
            definition_hash=hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        )
        self.db.add(policy)
        await self.db.flush()
        return policy

    async def execute_shadow_run(
        self, user: User, workspace_id: UUID, policy_id: UUID, baseline_definition_id: UUID,
        candidate_definition_id: UUID, dataset_version_id: UUID, table: CaptureTable | None = None,
    ) -> dict[str, Any]:
        """Run and persist one candidate gate against exact tenant-owned evidence."""
        workspace = await self._owned_workspace(user, workspace_id)
        policy = await self.db.get(RegressionPolicy, policy_id)
        if policy is None or policy.workspace_id != workspace.id:
            raise LookupError("Regression policy is unavailable in this workspace")
        definitions = {item.id: item for item in (await self.db.execute(
            select(MetricDefinition).join(Metric).where(
                MetricDefinition.id.in_([baseline_definition_id, candidate_definition_id]), Metric.workspace_id == workspace.id
            )
        )).scalars()}
        if set(definitions) != {baseline_definition_id, candidate_definition_id}:
            raise LookupError("Metric definitions are unavailable in this workspace")
        if definitions[baseline_definition_id].metric_id != definitions[candidate_definition_id].metric_id:
            raise ValueError("Shadow definitions must belong to the same metric")
        dataset = (await self.db.execute(select(DatasetVersion).join(MetricSource).where(
            DatasetVersion.id == dataset_version_id, DatasetVersion.status == "ready", MetricSource.workspace_id == workspace.id
        ))).scalars().first()
        if dataset is None:
            raise LookupError("Dataset version is unavailable in this workspace")
        store = snapshot_store_from_settings(get_settings())
        with tempfile.TemporaryDirectory(prefix="metrictrace-shadow-") as raw_temp:
            temp_dir = Path(raw_temp)
            path, identity = self._materialize_diff_object(store, workspace.id, dataset, table, temp_dir, "dataset")
            regression = check_sql_regression(
                str(path), definitions[baseline_definition_id].sql, definitions[candidate_definition_id].sql,
                max_absolute_difference=policy.max_absolute_difference,
                max_percent_difference=policy.max_percent_difference, allowed_roots=(str(temp_dir),),
            )
            contract_report = None
            if policy.required_contract_id:
                contract = await self.db.get(MetricContract, policy.required_contract_id)
                if contract is None or contract.workspace_id != workspace.id:
                    raise LookupError("Required contract is unavailable in this workspace")
                sql_name = str(identity["table"]).lower() if identity else "source_data"
                contract_report = evaluate_contracts(
                    {sql_name: str(path)}, contract.contracts, allowed_roots=(str(temp_dir),)
                )
        contract_status = PASS if not contract_report or contract_report["summary"]["mandatory_passed"] else "FAIL"
        status = PASS if regression["status"] == PASS and contract_status == PASS else "FAIL"
        report = {
            "dataset_table": identity,
            "dataset_content_hash": dataset.content_hash,
            "regression": regression,
            "required_contract": (
                {
                    "id": str(policy.required_contract_id),
                    "definition_hash": contract.definition_hash,
                    "report": contract_report,
                } if contract_report else None
            ),
            "policy_hash": policy.definition_hash,
        }
        fingerprint = hashlib.sha256(json.dumps({"policy": policy.definition_hash, "dataset": dataset.content_hash, "baseline": definitions[baseline_definition_id].normalized_sql_hash, "candidate": definitions[candidate_definition_id].normalized_sql_hash, "report": report}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        shadow = ShadowExecution(workspace_id=workspace.id, policy_id=policy.id, baseline_definition_id=baseline_definition_id, candidate_definition_id=candidate_definition_id, dataset_version_id=dataset.id, status=status, input_fingerprint=fingerprint, report=report)
        self.db.add(shadow)
        await self.db.flush()
        return {"id": str(shadow.id), "status": shadow.status, "policy_id": str(policy.id), "input_fingerprint": fingerprint, "report": report}

    async def promote_metric_definition(
        self, user: User, workspace_id: UUID, candidate_definition_id: UUID, shadow_execution_id: UUID
    ) -> dict[str, str | None]:
        """Activate a candidate only when its immutable PASS evidence remains current.

        The definition, policy, optional contract, and snapshot IDs are all read
        from the one-use shadow record rather than trusting client-supplied
        copies. The active-state change and its receipt share the request
        transaction.
        """
        workspace = await self._owned_workspace(user, workspace_id)
        shadow = await self.db.get(ShadowExecution, shadow_execution_id, with_for_update=True)
        if shadow is None or shadow.workspace_id != workspace.id:
            raise LookupError("Shadow execution is unavailable in this workspace")
        if shadow.status != PASS or shadow.candidate_definition_id != candidate_definition_id:
            raise ValueError("A matching PASS shadow execution is required for promotion.")
        existing = (
            await self.db.execute(select(MetricPromotion.id).where(MetricPromotion.shadow_execution_id == shadow.id))
        ).scalar_one_or_none()
        if existing:
            raise ValueError("This shadow execution has already authorized a promotion.")
        policy = await self.db.get(RegressionPolicy, shadow.policy_id)
        candidate = await self.db.get(MetricDefinition, candidate_definition_id, with_for_update=True)
        dataset = await self.db.get(DatasetVersion, shadow.dataset_version_id)
        if policy is None or candidate is None or dataset is None:
            raise ValueError("Promotion evidence is stale because a required binding is unavailable.")
        if candidate.lifecycle_state != "candidate":
            raise ValueError("Promotion evidence is stale because the definition is no longer a candidate.")
        metric = await self.db.get(Metric, candidate.metric_id)
        if metric is None or metric.workspace_id != workspace.id:
            raise LookupError("Candidate definition is unavailable in this workspace")
        report = shadow.report
        if report.get("policy_hash") != policy.definition_hash or report.get("regression", {}).get("status") != PASS:
            raise ValueError("Promotion evidence is stale because the regression policy binding changed.")
        if dataset.content_hash != report.get("dataset_content_hash"):
            raise ValueError("Promotion evidence is stale because the dataset binding changed.")
        required_contract = report.get("required_contract")
        if policy.required_contract_id:
            contract = await self.db.get(MetricContract, policy.required_contract_id)
            if not contract or not required_contract or required_contract.get("id") != str(contract.id) or required_contract.get("definition_hash") != contract.definition_hash:
                raise ValueError("Promotion evidence is stale because the contract binding changed.")
            if not required_contract["report"]["summary"]["mandatory_passed"]:
                raise ValueError("Promotion evidence does not satisfy the required contract.")
        elif required_contract is not None:
            raise ValueError("Promotion evidence is stale because its contract policy binding changed.")
        active_definitions = list((await self.db.execute(
            select(MetricDefinition).where(
                MetricDefinition.metric_id == metric.id,
                MetricDefinition.lifecycle_state == "active",
            ).with_for_update()
        )).scalars())
        for definition in active_definitions:
            definition.lifecycle_state = "superseded"
        candidate.lifecycle_state = "active"
        promotion = MetricPromotion(
            workspace_id=workspace.id,
            metric_id=metric.id,
            candidate_definition_id=candidate.id,
            previous_definition_id=active_definitions[0].id if active_definitions else None,
            shadow_execution_id=shadow.id,
            evidence_fingerprint=shadow.input_fingerprint,
        )
        self.db.add(promotion)
        await self.db.flush()
        return {
            "promotion_id": str(promotion.id),
            "candidate_definition_id": str(candidate.id),
            "previous_definition_id": str(active_definitions[0].id) if active_definitions else None,
            "evidence_fingerprint": promotion.evidence_fingerprint,
        }

    @staticmethod
    def _contract_read(contract: MetricContract, evaluation: ContractEvaluation | None = None) -> dict[str, Any]:
        return {
            "id": str(contract.id),
            "name": contract.name,
            "version": contract.version,
            "definition_hash": contract.definition_hash,
            "contracts": contract.contracts,
            "created_at": contract.created_at.isoformat(),
            "latest_evaluation": MetricTraceService._evaluation_read(evaluation) if evaluation else None,
        }

    @staticmethod
    def _evaluation_read(evaluation: ContractEvaluation) -> dict[str, Any]:
        return {
            "id": str(evaluation.id),
            "status": evaluation.status,
            "dataset_version_id": str(evaluation.dataset_version_id),
            "input_fingerprint": evaluation.input_fingerprint,
            "report": evaluation.report,
            "created_at": evaluation.created_at.isoformat(),
        }

    @staticmethod
    def _materialize_diff_object(
        store: Any,
        workspace_id: UUID,
        version: DatasetVersion,
        selected_table: CaptureTable | None,
        temp_dir: Path,
        label: str,
    ) -> tuple[Path, dict[str, str] | None]:
        """Resolve exactly one manifest object into a private bounded temp file."""
        try:
            manifest = json.loads(store.read(workspace_id, version.manifest_uri))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise DatasetDiffError("Dataset version manifest is unavailable or invalid.") from exc

        object_key: str
        identity: dict[str, str] | None = None
        tables = manifest.get("tables")
        if isinstance(tables, list):
            if selected_table is None:
                if len(tables) != 1:
                    raise DatasetDiffError("A table selection is required for a multi-table dataset version.")
                entry = tables[0]
            else:
                entry = next(
                    (
                        table
                        for table in tables
                        if table.get("schema") == selected_table.schema and table.get("table") == selected_table.table
                    ),
                    None,
                )
                if entry is None:
                    raise DatasetDiffError(f"Selected table {selected_table.identity} is unavailable in this dataset version.")
            object_key = str(entry.get("object", {}).get("key", ""))
            identity = {"schema": str(entry["schema"]), "table": str(entry["table"])}
        else:
            if selected_table is not None:
                raise DatasetDiffError("This single-table dataset version does not support a table selection.")
            objects = manifest.get("objects")
            if not isinstance(objects, list) or len(objects) != 1:
                raise DatasetDiffError("Dataset version does not contain one comparable Parquet object.")
            relative_key = objects[0].get("key")
            if not isinstance(relative_key, str) or not relative_key.endswith(".parquet"):
                raise DatasetDiffError("Dataset version does not contain a Parquet object.")
            object_key = f"{version.manifest_uri.rsplit('/', 1)[0]}/{relative_key}"

        if not object_key.endswith(".parquet"):
            raise DatasetDiffError("Dataset version does not contain a Parquet object.")
        destination = temp_dir / f"{label}.parquet"
        try:
            destination.write_bytes(store.read(workspace_id, object_key))
        except (OSError, ValueError) as exc:
            raise DatasetDiffError("Dataset version object is unavailable.") from exc
        return destination, identity

    @staticmethod
    def _materialize_join_objects(
        store: Any, workspace_id: UUID, version: DatasetVersion, temp_dir: Path
    ) -> tuple[dict[str, str], list[dict[str, str]]]:
        """Materialize approved manifest tables with deterministic SQL names."""
        try:
            manifest = json.loads(store.read(workspace_id, version.manifest_uri))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise JoinAuditError("Dataset version manifest is unavailable or invalid.") from exc
        datasets: dict[str, str] = {}
        identities: list[dict[str, str]] = []
        entries = manifest.get("tables")
        if isinstance(entries, list):
            for entry in entries:
                schema, table = entry.get("schema"), entry.get("table")
                object_key = entry.get("object", {}).get("key")
                name = str(table).lower() if isinstance(table, str) else ""
                if not schema or not name or not isinstance(object_key, str) or not object_key.endswith(".parquet"):
                    raise JoinAuditError("Dataset version has an invalid captured-table manifest.")
                if name in datasets:
                    raise JoinAuditError("Captured table names must be unique across schemas for join auditing.")
                destination = temp_dir / f"{name}.parquet"
                try:
                    destination.write_bytes(store.read(workspace_id, object_key))
                except (OSError, ValueError) as exc:
                    raise JoinAuditError(f"Captured table {schema}.{table} is unavailable.") from exc
                datasets[name] = str(destination)
                identities.append({"schema": str(schema), "table": str(table), "sql_name": name})
        else:
            path, _ = MetricTraceService._materialize_diff_object(store, workspace_id, version, None, temp_dir, "source_data")
            datasets["source_data"] = str(path)
            identities.append({"schema": "", "table": "source_data", "sql_name": "source_data"})
        if not datasets:
            raise JoinAuditError("Dataset version contains no auditable tables.")
        return datasets, identities

    async def enqueue_scheduled_postgres_captures(self, now: datetime | None = None) -> int:
        """Queue due captures using stable time windows as durable idempotency keys.

        The scheduler does not access credentials or source data. Multiple
        scheduler processes can observe the same source; the durable-job
        uniqueness constraint makes a window's capture authoritative once.
        """
        now = now or datetime.now(timezone.utc)
        result = await self.db.execute(
            select(MetricSource).join(DBConnection, MetricSource.connection_id == DBConnection.id).where(
                MetricSource.source_type == "postgresql", DBConnection.is_active.is_(True)
            )
        )
        queue = DurableJobQueue(self.db, get_settings().metrictrace_job_lease_seconds)
        enqueued = 0
        for source in result.scalars():
            interval = source.capture_config.get("schedule_seconds")
            if isinstance(interval, bool) or not isinstance(interval, int) or interval < 300:
                continue
            if source.capture_status in {"queued", "capturing"}:
                continue
            window = int(now.timestamp()) // interval
            job = await queue.enqueue(
                source.workspace_id,
                "SNAPSHOT_CAPTURE",
                {"source_id": str(source.id), "scheduled": True},
                f"scheduled-snapshot-capture:{source.id}:{window}",
                max_attempts=3,
            )
            if job.status == "QUEUED":
                source.capture_status = "queued"
                enqueued += 1
        await self.db.flush()
        return enqueued

    async def enqueue_postgres_capture(self, user: User, workspace_id: UUID, source_id: UUID):
        """Queue a user-authorized capture; credentials never enter the job payload."""
        await self._owned_workspace(user, workspace_id)
        result = await self.db.execute(
            select(MetricSource).where(
                MetricSource.id == source_id,
                MetricSource.workspace_id == workspace_id,
                MetricSource.source_type == "postgresql",
            )
        )
        source = result.scalars().first()
        if source is None or source.connection_id is None:
            raise LookupError("PostgreSQL source not found")
        connection = await ConnectionService(self.db).get_connection(source.connection_id, user.id)
        if connection is None or not connection.is_active:
            raise LookupError("The source connection is unavailable.")
        source.capture_status = "queued"
        job = await DurableJobQueue(self.db, get_settings().metrictrace_job_lease_seconds).enqueue(
            workspace_id,
            "SNAPSHOT_CAPTURE",
            {"source_id": str(source.id)},
            f"snapshot-capture:{source.id}:{uuid.uuid4()}",
            max_attempts=3,
        )
        await self.db.flush()
        return job

    async def execute_postgres_capture(self, workspace_id: UUID, source_id: UUID) -> DatasetVersion:
        """Worker-only capture execution after API authorization and queue fencing.

        The source read happens after committing the short metadata state update,
        so a worker never holds a metadata transaction while reading PostgreSQL
        or uploading Parquet objects.
        """
        result = await self.db.execute(
            select(MetricSource, DBConnection)
            .join(DBConnection, MetricSource.connection_id == DBConnection.id)
            .where(
                MetricSource.id == source_id,
                MetricSource.workspace_id == workspace_id,
                MetricSource.source_type == "postgresql",
                DBConnection.is_active.is_(True),
            )
        )
        row = result.first()
        if row is None:
            raise LookupError("PostgreSQL source or active connection not found")
        source, connection = row
        configured_tables = [CaptureTable(**entry) for entry in source.capture_config.get("tables", [])]
        if not configured_tables:
            raise ValueError("The source has no selected tables.")
        connection_string = ConnectionService(self.db).build_connection_string(connection)
        source.capture_status = "capturing"
        await self.db.commit()

        settings = get_settings()
        limits = CaptureLimits(
            batch_rows=settings.metrictrace_capture_batch_rows,
            max_tables=settings.metrictrace_capture_max_tables,
            max_rows=settings.metrictrace_capture_max_rows,
            max_bytes=settings.metrictrace_capture_max_bytes,
            timeout_seconds=settings.metrictrace_capture_timeout_seconds,
        )
        try:
            snapshot = await PostgresSnapshotCapture(snapshot_store_from_settings(settings), limits).capture(
                connection_string, workspace_id, source.id, configured_tables
            )
        except Exception:
            # This starts a new, short metadata transaction after source I/O.
            source.capture_status = "failed"
            await self.db.commit()
            raise

        parent_result = await self.db.execute(
            select(DatasetVersion.id)
            .where(DatasetVersion.source_id == source.id, DatasetVersion.status == "ready")
            .order_by(DatasetVersion.captured_at.desc())
            .limit(1)
        )
        version = DatasetVersion(
            source_id=source.id,
            parent_version_id=parent_result.scalar_one_or_none(),
            manifest_uri=snapshot.manifest_key,
            content_hash=snapshot.content_hash,
            row_count=snapshot.row_count,
            byte_size=snapshot.byte_size,
            schema_json=snapshot.schema,
            consistency_level="postgresql_repeatable_read",
            status="ready",
        )
        source.capture_status = "ready"
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def capture_job_for_user(
        self, user: User, workspace_id: UUID, source_id: UUID, job_id: UUID
    ):
        """Read a capture job only when its workspace and source both match."""
        await self._owned_workspace(user, workspace_id)
        job = await self.db.get(DurableJob, job_id)
        if (
            job is None
            or job.workspace_id != workspace_id
            or job.job_type != "SNAPSHOT_CAPTURE"
            or job.input_payload.get("source_id") != str(source_id)
        ):
            raise LookupError("Snapshot capture job not found")
        return job

    async def replay_options_for_user(self, user: User, workspace_id: UUID) -> dict[str, list[dict[str, str]]]:
        """Return only workspace-owned immutable replay inputs for the UI."""
        await self._owned_workspace(user, workspace_id)
        versions = await self.db.execute(
            select(DatasetVersion, MetricSource)
            .join(MetricSource, DatasetVersion.source_id == MetricSource.id)
            .where(MetricSource.workspace_id == workspace_id, DatasetVersion.status == "ready")
            .order_by(DatasetVersion.captured_at.desc())
        )
        definitions = await self.db.execute(
            select(MetricDefinition, Metric)
            .join(Metric, MetricDefinition.metric_id == Metric.id)
            .where(Metric.workspace_id == workspace_id)
            .order_by(Metric.name, MetricDefinition.version)
        )
        return {
            "dataset_versions": [
                {"id": str(version.id), "source_id": str(source.id), "source_name": source.name,
                 "captured_at": version.captured_at.isoformat(), "content_hash": version.content_hash}
                for version, source in versions
            ],
            "metric_definitions": [
                {"id": str(definition.id), "metric_id": str(metric.id), "metric_name": metric.name,
                 "version": str(definition.version), "sql_hash": definition.normalized_sql_hash}
                for definition, metric in definitions
            ],
        }

    async def replay_workspace_for_user(self, user: User) -> dict[str, Any]:
        """Return the caller's default workspace and its authorized replay inputs.

        The web client must never infer a workspace identifier from local state.
        Creating an empty default workspace is the same behavior used by the
        existing MetricTrace entry points and does not create fixture data.
        """
        workspace = await self.workspace_for_user(user)
        return {
            "workspace_id": str(workspace.id),
            "options": await self.replay_options_for_user(user, workspace.id),
        }

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
            job.attribution = four_way_attribution(old_old, old_new, new_old, new_new)
            job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return job

    async def submit_replay(self, user: User, workspace_id: UUID, old_version_id: UUID, new_version_id: UUID, old_definition_id: UUID, new_definition_id: UUID) -> ReplayJob:
        """Persist four immutable replay cells and enqueue independent workers."""
        workspace = await self._owned_workspace(user, workspace_id)
        versions = await self.db.execute(select(DatasetVersion, MetricSource).join(MetricSource, DatasetVersion.source_id == MetricSource.id).where(DatasetVersion.id.in_([old_version_id, new_version_id]), MetricSource.workspace_id == workspace.id, DatasetVersion.status == "ready"))
        owned_versions = {version.id: version for version, _ in versions.all()}
        definitions = await self.db.execute(select(MetricDefinition).join(Metric).where(MetricDefinition.id.in_([old_definition_id, new_definition_id]), Metric.workspace_id == workspace.id))
        owned_definitions = {definition.id: definition for definition in definitions.scalars().all()}
        if set(owned_versions) != {old_version_id, new_version_id} or set(owned_definitions) != {old_definition_id, new_definition_id}:
            raise LookupError("Replay inputs are unavailable in this workspace")
        if owned_versions[old_version_id].source_id != owned_versions[new_version_id].source_id:
            raise ValueError("Replay dataset versions must belong to the same data source")
        if owned_definitions[old_definition_id].metric_id != owned_definitions[new_definition_id].metric_id:
            raise ValueError("Replay definitions must belong to the same metric")
        replay = ReplayJob(workspace_id=workspace.id, status="queued")
        self.db.add(replay)
        await self.db.flush()
        queue = DurableJobQueue(self.db, get_settings().metrictrace_job_lease_seconds)
        for label, definition_id, version_id in (("old_data_old_definition", old_definition_id, old_version_id), ("old_data_new_definition", new_definition_id, old_version_id), ("new_data_old_definition", old_definition_id, new_version_id), ("new_data_new_definition", new_definition_id, new_version_id)):
            definition, version = owned_definitions[definition_id], owned_versions[version_id]
            fingerprint = hashlib.sha256(f"{workspace.id}:{version.content_hash}:{definition.normalized_sql_hash}:v1".encode()).hexdigest()
            cell = ReplayCell(replay_job_id=replay.id, label=label, definition_id=definition_id, dataset_version_id=version_id, status="queued", execution_fingerprint=fingerprint)
            self.db.add(cell)
            await self.db.flush()
            durable = await queue.enqueue(workspace.id, "REPLAY_CELL_EXECUTION", {"cell_id": str(cell.id)}, f"replay-cell:{cell.id}")
            cell.durable_job_id = durable.id
        await self.db.flush()
        return replay

    async def cancel_replay(self, user: User, replay_id: UUID) -> ReplayJob:
        """Cancel a replay and fence every cell from publishing further results."""
        replay = await self.db.get(ReplayJob, replay_id, with_for_update=True)
        if replay is None:
            raise LookupError("Replay not found")
        await self._owned_workspace(user, replay.workspace_id)
        if replay.status in {"completed", "failed", "cancelled"}:
            return replay

        cells = list(
            (
                await self.db.execute(
                    select(ReplayCell).where(ReplayCell.replay_job_id == replay.id).with_for_update()
                )
            ).scalars()
        )
        queue = DurableJobQueue(self.db, get_settings().metrictrace_job_lease_seconds)
        for cell in cells:
            if cell.durable_job_id:
                durable = await self.db.get(DurableJob, cell.durable_job_id, with_for_update=True)
                if durable is not None:
                    await queue.cancel(durable)
            if cell.status not in {"completed", "failed", "cancelled"}:
                cell.status, cell.error = "cancelled", "Cancelled by an authorized user."
        replay.status, replay.completed_at = "cancelled", datetime.now(timezone.utc)
        await self.db.flush()
        return replay

    async def execute_queued_cell(self, cell_id: UUID, queue: DurableJobQueue, worker_id: str, fencing_token: int) -> dict:
        # Read and mark the cell in a short metadata transaction. Computation
        # happens only after the commit below, so a slow DuckDB query never
        # holds a row lock or metadata transaction.
        cell = await self.db.get(ReplayCell, cell_id)
        if not cell or not cell.durable_job_id:
            raise LookupError("Replay cell not found")
        if cell.status == "completed":
            return {"cell_id": str(cell.id), "status": cell.status}
        cell.status = "running"
        definition = await self.db.get(MetricDefinition, cell.definition_id)
        version = await self.db.get(DatasetVersion, cell.dataset_version_id)
        await self.db.commit()
        try:
            result, duration = await self._execute_cell(definition, version)
            await queue._owned(cell.durable_job_id, worker_id, fencing_token)
            cell = await self.db.get(ReplayCell, cell_id, with_for_update=True)
            if cell is None or cell.status == "completed":
                return {"cell_id": str(cell_id), "status": "completed"}
            cell.result_text, cell.duration_ms, cell.status, cell.error = result, duration, "completed", None
            self.db.add(MetricObservation(definition_id=cell.definition_id, dataset_version_id=cell.dataset_version_id, result_text=result, status="completed", duration_ms=duration))
        except Exception as exc:
            await queue._owned(cell.durable_job_id, worker_id, fencing_token)
            failed = await self.db.get(ReplayCell, cell_id, with_for_update=True)
            if failed is not None:
                failed.status, failed.error = "failed", str(exc)
            raise
        await self._finalize_replay(cell.replay_job_id)
        return {"cell_id": str(cell.id), "status": cell.status, "duration_ms": cell.duration_ms}

    async def _finalize_replay(self, replay_id: UUID) -> None:
        replay = await self.db.get(ReplayJob, replay_id, with_for_update=True)
        cells = list((await self.db.execute(select(ReplayCell).where(ReplayCell.replay_job_id == replay_id))).scalars())
        if any(cell.status == "failed" for cell in cells):
            replay.status = "failed"
            replay.completed_at = datetime.now(timezone.utc)
        elif len(cells) == 4 and all(cell.status == "completed" for cell in cells):
            values = {cell.label: Decimal(cell.result_text) for cell in cells}
            replay.attribution = four_way_attribution(values["old_data_old_definition"], values["old_data_new_definition"], values["new_data_old_definition"], values["new_data_new_definition"])
            replay.status, replay.completed_at = "completed", datetime.now(timezone.utc)
        elif any(cell.status == "running" for cell in cells):
            replay.status = "running"

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
                {"order_id": "a-1", "amount_inr": 2_100_000, "status": "paid", "channel": "direct"},
                {"order_id": "a-2", "amount_inr": 300_000, "status": "paid", "channel": "marketplace"},
            ]
            new_records = [
                {"order_id": "a-1", "amount_inr": 1_800_000, "status": "paid", "channel": "direct"},
                {"order_id": "a-2", "amount_inr": 420_000, "status": "paid", "channel": "marketplace"},
            ]
            old_version = await self.capture_records(workspace, source, old_records)
            new_version = await self.capture_records(workspace, source, new_records, old_version.id)
            metric = Metric(workspace_id=workspace.id, name="Monday revenue", description="Paid order revenue in INR")
            self.db.add(metric)
            await self.db.flush()
            original_sql = "SELECT SUM(amount_inr) FROM source_data WHERE status = 'paid'"
            proposed_sql = "SELECT SUM(amount_inr) FROM source_data WHERE status = 'paid' AND channel <> 'marketplace'"
            old_definition = MetricDefinition(metric_id=metric.id, version=1, sql=original_sql, normalized_sql_hash=self._sql_hash(original_sql), unit="INR", currency="INR")
            new_definition = MetricDefinition(metric_id=metric.id, version=2, sql=proposed_sql, normalized_sql_hash=self._sql_hash(proposed_sql), unit="INR", currency="INR", lifecycle_state="candidate")
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
            "headline": "Four exact executions reconstruct the ₹24 lakh to ₹18 lakh metric regression.",
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
