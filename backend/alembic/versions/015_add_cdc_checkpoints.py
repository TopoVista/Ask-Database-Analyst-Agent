"""add tenant-scoped CDC checkpoints

Revision ID: 015_add_cdc_checkpoints
Revises: 014_add_bitemporal_snapshot_metadata
"""
from alembic import op
import sqlalchemy as sa

revision = "015_add_cdc_checkpoints"
down_revision = "014_add_bitemporal_snapshot_metadata"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("cdc_checkpoints", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("workspace_id", sa.Uuid(), nullable=False), sa.Column("source_id", sa.Uuid(), nullable=False), sa.Column("acknowledged_lsn", sa.String(32)), sa.Column("accepted_event_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["source_id"], ["metric_sources.id"], ondelete="CASCADE"), sa.UniqueConstraint("source_id", name="uq_cdc_checkpoint_source"))

def downgrade():
    op.drop_table("cdc_checkpoints")
