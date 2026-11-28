"""Tenant-scoped metadata for MetricTrace's reproducible metric runtime.

The data objects themselves live in immutable storage; these rows only point
to published manifests and preserve the exact inputs of every execution.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_limit_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=1_073_741_824)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MetricSource(Base):
    __tablename__ = "metric_sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="import")
    connection_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("db_connections.id", ondelete="RESTRICT"))
    capture_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    capture_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    capabilities: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("metric_sources.id", ondelete="CASCADE"), nullable=False)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("dataset_versions.id"))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    manifest_uri: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    consistency_level: Mapped[str] = mapped_column(String(32), nullable=False, default="import")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")


class Metric(Base):
    __tablename__ = "metrics"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_metric_workspace_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"
    __table_args__ = (UniqueConstraint("metric_id", "version", name="uq_metric_definition_version"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    metric_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("metrics.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    sql: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_sql_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(8))
    unit: Mapped[str] = mapped_column(String(64), nullable=False, default="count")
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MetricObservation(Base):
    __tablename__ = "metric_observations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    definition_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("metric_definitions.id"), nullable=False)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("dataset_versions.id"), nullable=False)
    result_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MetricContract(Base):
    """An immutable, workspace-scoped version of a declarative contract set."""

    __tablename__ = "metric_contracts"
    __table_args__ = (UniqueConstraint("workspace_id", "name", "version", name="uq_metric_contract_version"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    contracts: Mapped[list] = mapped_column(JSON, nullable=False)
    definition_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ContractEvaluation(Base):
    """Durable evidence from evaluating one exact contract version and snapshot."""

    __tablename__ = "contract_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    contract_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("metric_contracts.id", ondelete="CASCADE"), nullable=False)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("dataset_versions.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    report: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RegressionPolicy(Base):
    """An immutable gate policy referenced by persisted shadow executions."""

    __tablename__ = "regression_policies"
    __table_args__ = (UniqueConstraint("workspace_id", "name", "version", name="uq_regression_policy_version"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    max_absolute_difference: Mapped[str | None] = mapped_column(String(128))
    max_percent_difference: Mapped[str | None] = mapped_column(String(128))
    required_contract_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("metric_contracts.id", ondelete="RESTRICT"))
    definition_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ShadowExecution(Base):
    """One candidate-versus-baseline gate on an exact immutable evidence set."""

    __tablename__ = "shadow_executions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    policy_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("regression_policies.id", ondelete="RESTRICT"), nullable=False)
    baseline_definition_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("metric_definitions.id", ondelete="RESTRICT"), nullable=False)
    candidate_definition_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("metric_definitions.id", ondelete="RESTRICT"), nullable=False)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("dataset_versions.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    report: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MetricPromotion(Base):
    """An auditable, one-time activation authorized by a PASS shadow run."""

    __tablename__ = "metric_promotions"
    __table_args__ = (UniqueConstraint("shadow_execution_id", name="uq_metric_promotion_shadow_execution"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    metric_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("metrics.id", ondelete="RESTRICT"), nullable=False)
    candidate_definition_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("metric_definitions.id", ondelete="RESTRICT"), nullable=False)
    previous_definition_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("metric_definitions.id", ondelete="RESTRICT"))
    shadow_execution_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("shadow_executions.id", ondelete="RESTRICT"), nullable=False)
    evidence_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class DecisionReceipt(Base):
    """Immutable platform evidence for one completed four-way replay."""

    __tablename__ = "decision_receipts"
    __table_args__ = (UniqueConstraint("replay_job_id", name="uq_decision_receipt_replay"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    replay_job_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("replay_jobs.id", ondelete="RESTRICT"), nullable=False)
    integrity_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ReplayJob(Base):
    __tablename__ = "replay_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    attribution: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DurableJob(Base):
    """Lease-owned unit of worker execution; payloads contain IDs, never secrets."""
    __tablename__ = "durable_jobs"
    __table_args__ = (UniqueConstraint("workspace_id", "idempotency_key", name="uq_durable_job_idempotency"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    parent_job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("durable_jobs.id", ondelete="CASCADE"))
    job_type: Mapped[str] = mapped_column(String(48), nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="QUEUED")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fencing_token: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancellation_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    result_reference: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReplayCell(Base):
    __tablename__ = "replay_cells"
    __table_args__ = (UniqueConstraint("replay_job_id", "label", name="uq_replay_cell_label"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    replay_job_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("replay_jobs.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    definition_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("metric_definitions.id"), nullable=False)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("dataset_versions.id"), nullable=False)
    result_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    durable_job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("durable_jobs.id"))
    execution_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, default="")


Index("idx_workspace_members_user", WorkspaceMember.user_id)
Index("idx_metric_sources_workspace", MetricSource.workspace_id)
Index("idx_dataset_versions_source_capture", DatasetVersion.source_id, DatasetVersion.captured_at)
Index("idx_metrics_workspace", Metric.workspace_id)
Index("idx_metric_contracts_workspace_name", MetricContract.workspace_id, MetricContract.name)
Index("idx_contract_evaluations_workspace_created", ContractEvaluation.workspace_id, ContractEvaluation.created_at)
Index("idx_contract_evaluations_contract_created", ContractEvaluation.contract_id, ContractEvaluation.created_at)
Index("idx_regression_policies_workspace_name", RegressionPolicy.workspace_id, RegressionPolicy.name)
Index("idx_shadow_executions_workspace_created", ShadowExecution.workspace_id, ShadowExecution.created_at)
Index("idx_metric_promotions_workspace_created", MetricPromotion.workspace_id, MetricPromotion.created_at)
Index("idx_decision_receipts_workspace_created", DecisionReceipt.workspace_id, DecisionReceipt.created_at)
Index("idx_replay_jobs_workspace_created", ReplayJob.workspace_id, ReplayJob.created_at)
Index("idx_durable_jobs_claim", DurableJob.status, DurableJob.scheduled_at, DurableJob.priority)
