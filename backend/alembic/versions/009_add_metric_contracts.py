"""persist immutable MetricTrace contract definitions and evaluations

Revision ID: 009_add_metric_contracts
Revises: 008_add_postgres_capture_sources
"""

from alembic import op
import sqlalchemy as sa


revision = "009_add_metric_contracts"
down_revision = "008_add_postgres_capture_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "metric_contracts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("contracts", sa.JSON(), nullable=False),
        sa.Column("definition_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "name", "version", name="uq_metric_contract_version"),
    )
    op.create_index("idx_metric_contracts_workspace_name", "metric_contracts", ["workspace_id", "name"])
    op.create_table(
        "contract_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_version_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["metric_contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_contract_evaluations_workspace_created", "contract_evaluations", ["workspace_id", "created_at"])
    op.create_index("idx_contract_evaluations_contract_created", "contract_evaluations", ["contract_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_contract_evaluations_contract_created", table_name="contract_evaluations")
    op.drop_index("idx_contract_evaluations_workspace_created", table_name="contract_evaluations")
    op.drop_table("contract_evaluations")
    op.drop_index("idx_metric_contracts_workspace_name", table_name="metric_contracts")
    op.drop_table("metric_contracts")
