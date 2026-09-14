"""add durable RAG document chunks

Revision ID: 003_add_rag_document_chunks
Revises: 002_add_datasets
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "003_add_rag_document_chunks"
down_revision = "002_add_datasets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("rag_document_chunks"):
        return
    op.create_table(
        "rag_document_chunks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=512), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding_json", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_rag_document_chunks_user_source", "rag_document_chunks", ["user_id", "source"])


def downgrade() -> None:
    op.drop_index("idx_rag_document_chunks_user_source", table_name="rag_document_chunks")
    op.drop_table("rag_document_chunks")
