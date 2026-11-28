"""add source and knowledge time metadata for historical versions

Revision ID: 014_add_bitemporal_snapshot_metadata
Revises: 013_add_metric_lineage_snapshots
"""

from alembic import op
import sqlalchemy as sa


revision = "014_add_bitemporal_snapshot_metadata"
down_revision = "013_add_metric_lineage_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("dataset_versions") as batch:
        batch.add_column(sa.Column("source_snapshot_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("knowledge_recorded_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("temporal_summary", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    with op.batch_alter_table("dataset_versions") as batch:
        batch.drop_column("temporal_summary")
        batch.drop_column("knowledge_recorded_at")
        batch.drop_column("source_snapshot_at")
