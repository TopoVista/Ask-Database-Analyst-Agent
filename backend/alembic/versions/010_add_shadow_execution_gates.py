"""persist immutable SQL regression policies and shadow execution evidence

Revision ID: 010_add_shadow_execution_gates
Revises: 009_add_metric_contracts
"""

from alembic import op
import sqlalchemy as sa


revision = "010_add_shadow_execution_gates"
down_revision = "009_add_metric_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regression_policies",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("max_absolute_difference", sa.String(length=128)), sa.Column("max_percent_difference", sa.String(length=128)),
        sa.Column("required_contract_id", sa.Uuid()), sa.Column("definition_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["required_contract_id"], ["metric_contracts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("workspace_id", "name", "version", name="uq_regression_policy_version"),
    )
    op.create_index("idx_regression_policies_workspace_name", "regression_policies", ["workspace_id", "name"])
    op.create_table(
        "shadow_executions",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False), sa.Column("baseline_definition_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_definition_id", sa.Uuid(), nullable=False), sa.Column("dataset_version_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False), sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["policy_id"], ["regression_policies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["baseline_definition_id"], ["metric_definitions.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["candidate_definition_id"], ["metric_definitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_shadow_executions_workspace_created", "shadow_executions", ["workspace_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_shadow_executions_workspace_created", table_name="shadow_executions")
    op.drop_table("shadow_executions")
    op.drop_index("idx_regression_policies_workspace_name", table_name="regression_policies")
    op.drop_table("regression_policies")
