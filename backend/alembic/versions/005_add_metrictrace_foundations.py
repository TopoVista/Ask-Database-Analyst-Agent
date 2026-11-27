"""add MetricTrace immutable replay foundations

Revision ID: 005_add_metrictrace_foundations
Revises: 004_remove_rag_document_chunks
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "005_add_metrictrace_foundations"
down_revision = "004_remove_rag_document_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("storage_limit_bytes", sa.Integer(), nullable=False, server_default="1073741824"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "workspace_members",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="owner"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )
    op.create_index("idx_workspace_members_user", "workspace_members", ["user_id"])
    op.create_table(
        "metric_sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("capture_status", sa.String(32), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_metric_sources_workspace", "metric_sources", ["workspace_id"])
    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("metric_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_version_id", sa.Uuid(), sa.ForeignKey("dataset_versions.id")),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("manifest_uri", sa.String(1024), nullable=False, unique=True),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("schema_json", sa.JSON(), nullable=False),
        sa.Column("consistency_level", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
    )
    op.create_index("idx_dataset_versions_source_capture", "dataset_versions", ["source_id", "captured_at"])
    op.create_table(
        "metrics",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "name", name="uq_metric_workspace_name"),
    )
    op.create_index("idx_metrics_workspace", "metrics", ["workspace_id"])
    op.create_table(
        "metric_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("metric_id", sa.Uuid(), sa.ForeignKey("metrics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("sql", sa.Text(), nullable=False),
        sa.Column("normalized_sql_hash", sa.String(64), nullable=False),
        sa.Column("currency", sa.String(8)),
        sa.Column("unit", sa.String(64), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("metric_id", "version", name="uq_metric_definition_version"),
    )
    op.create_table(
        "metric_observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("definition_id", sa.Uuid(), sa.ForeignKey("metric_definitions.id"), nullable=False),
        sa.Column("dataset_version_id", sa.Uuid(), sa.ForeignKey("dataset_versions.id"), nullable=False),
        sa.Column("result_text", sa.Text()), sa.Column("status", sa.String(32), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False), sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "replay_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False), sa.Column("attribution", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_replay_jobs_workspace_created", "replay_jobs", ["workspace_id", "created_at"])
    op.create_table(
        "replay_cells",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("replay_job_id", sa.Uuid(), sa.ForeignKey("replay_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("definition_id", sa.Uuid(), sa.ForeignKey("metric_definitions.id"), nullable=False),
        sa.Column("dataset_version_id", sa.Uuid(), sa.ForeignKey("dataset_versions.id"), nullable=False),
        sa.Column("result_text", sa.Text()), sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error", sa.Text()), sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.UniqueConstraint("replay_job_id", "label", name="uq_replay_cell_label"),
    )


def downgrade() -> None:
    op.drop_table("replay_cells")
    op.drop_index("idx_replay_jobs_workspace_created", table_name="replay_jobs")
    op.drop_table("replay_jobs")
    op.drop_table("metric_observations")
    op.drop_table("metric_definitions")
    op.drop_index("idx_metrics_workspace", table_name="metrics")
    op.drop_table("metrics")
    op.drop_index("idx_dataset_versions_source_capture", table_name="dataset_versions")
    op.drop_table("dataset_versions")
    op.drop_index("idx_metric_sources_workspace", table_name="metric_sources")
    op.drop_table("metric_sources")
    op.drop_index("idx_workspace_members_user", table_name="workspace_members")
    op.drop_table("workspace_members")
    op.drop_table("workspaces")
