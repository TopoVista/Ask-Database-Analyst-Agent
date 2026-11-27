"""associate MetricTrace sources with encrypted registered connections

Revision ID: 008_add_postgres_capture_sources
Revises: 007_connect_replay_cells_to_jobs
"""

from alembic import op
import sqlalchemy as sa

revision = "008_add_postgres_capture_sources"
down_revision = "007_connect_replay_cells_to_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("metric_sources") as batch:
        batch.add_column(sa.Column("connection_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("capture_config", sa.JSON(), nullable=False, server_default="{}"))
        batch.create_foreign_key("fk_metric_sources_connection", "db_connections", ["connection_id"], ["id"], ondelete="RESTRICT")


def downgrade() -> None:
    with op.batch_alter_table("metric_sources") as batch:
        batch.drop_constraint("fk_metric_sources_connection", type_="foreignkey")
        batch.drop_column("capture_config")
        batch.drop_column("connection_id")
