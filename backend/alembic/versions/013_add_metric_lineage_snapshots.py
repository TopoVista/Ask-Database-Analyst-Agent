"""persist version-bound metric lineage snapshots

Revision ID: 013_add_metric_lineage_snapshots
Revises: 012_add_decision_receipts
"""

from alembic import op
import sqlalchemy as sa

revision = "013_add_metric_lineage_snapshots"
down_revision = "012_add_decision_receipts"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("metric_lineage_snapshots", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("workspace_id", sa.Uuid(), nullable=False), sa.Column("definition_id", sa.Uuid(), nullable=False), sa.Column("dataset_version_id", sa.Uuid(), nullable=False), sa.Column("fingerprint", sa.String(length=64), nullable=False), sa.Column("report", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["definition_id"], ["metric_definitions.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("definition_id", "dataset_version_id", name="uq_metric_lineage_snapshot"))
    op.create_index("idx_metric_lineage_workspace_created", "metric_lineage_snapshots", ["workspace_id", "created_at"])

def downgrade() -> None:
    op.drop_index("idx_metric_lineage_workspace_created", table_name="metric_lineage_snapshots")
    op.drop_table("metric_lineage_snapshots")
