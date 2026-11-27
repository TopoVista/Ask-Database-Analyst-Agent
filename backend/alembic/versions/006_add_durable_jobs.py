"""add durable worker job queue

Revision ID: 006_add_durable_jobs
Revises: 005_add_metrictrace_foundations
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "006_add_durable_jobs"
down_revision = "005_add_metrictrace_foundations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "durable_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_job_id", sa.Uuid(), sa.ForeignKey("durable_jobs.id", ondelete="CASCADE")),
        sa.Column("job_type", sa.String(48), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("lease_owner", sa.String(128)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("fencing_token", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cancellation_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("result_reference", sa.JSON()),
        sa.Column("error", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_durable_job_idempotency"),
    )
    op.create_index("idx_durable_jobs_claim", "durable_jobs", ["status", "scheduled_at", "priority"])


def downgrade() -> None:
    op.drop_index("idx_durable_jobs_claim", table_name="durable_jobs")
    op.drop_table("durable_jobs")
