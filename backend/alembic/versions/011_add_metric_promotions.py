"""record transactional metric activations authorized by shadow evidence

Revision ID: 011_add_metric_promotions
Revises: 010_add_shadow_execution_gates
"""

from alembic import op
import sqlalchemy as sa


revision = "011_add_metric_promotions"
down_revision = "010_add_shadow_execution_gates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "metric_promotions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("metric_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_definition_id", sa.Uuid(), nullable=False),
        sa.Column("previous_definition_id", sa.Uuid()),
        sa.Column("shadow_execution_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["metric_id"], ["metrics.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["candidate_definition_id"], ["metric_definitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["previous_definition_id"], ["metric_definitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shadow_execution_id"], ["shadow_executions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shadow_execution_id", name="uq_metric_promotion_shadow_execution"),
    )
    op.create_index("idx_metric_promotions_workspace_created", "metric_promotions", ["workspace_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_metric_promotions_workspace_created", table_name="metric_promotions")
    op.drop_table("metric_promotions")
