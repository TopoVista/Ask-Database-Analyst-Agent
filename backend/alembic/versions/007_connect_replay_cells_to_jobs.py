"""connect replay cells to durable jobs

Revision ID: 007_connect_replay_cells_to_jobs
Revises: 006_add_durable_jobs
"""
from alembic import op
import sqlalchemy as sa

revision = "007_connect_replay_cells_to_jobs"
down_revision = "006_add_durable_jobs"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Batch mode keeps SQLite development migration smoke tests equivalent to
    # PostgreSQL schema evolution, where ALTER TABLE can add the FK directly.
    with op.batch_alter_table("replay_cells") as batch:
        batch.add_column(sa.Column("durable_job_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("execution_fingerprint", sa.String(64), nullable=False, server_default=""))
        batch.create_foreign_key("fk_replay_cells_durable_job", "durable_jobs", ["durable_job_id"], ["id"])

def downgrade() -> None:
    with op.batch_alter_table("replay_cells") as batch:
        batch.drop_constraint("fk_replay_cells_durable_job", type_="foreignkey")
        batch.drop_column("execution_fingerprint")
        batch.drop_column("durable_job_id")
