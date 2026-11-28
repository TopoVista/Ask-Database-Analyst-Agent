"""persist immutable platform decision receipts

Revision ID: 012_add_decision_receipts
Revises: 011_add_metric_promotions
"""

from alembic import op
import sqlalchemy as sa

revision = "012_add_decision_receipts"
down_revision = "011_add_metric_promotions"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("decision_receipts", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("workspace_id", sa.Uuid(), nullable=False), sa.Column("replay_job_id", sa.Uuid(), nullable=False), sa.Column("integrity_sha256", sa.String(length=64), nullable=False), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["replay_job_id"], ["replay_jobs.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("replay_job_id", name="uq_decision_receipt_replay"))
    op.create_index("idx_decision_receipts_workspace_created", "decision_receipts", ["workspace_id", "created_at"])

def downgrade() -> None:
    op.drop_index("idx_decision_receipts_workspace_created", table_name="decision_receipts")
    op.drop_table("decision_receipts")
