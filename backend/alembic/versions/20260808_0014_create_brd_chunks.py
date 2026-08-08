"""Create brd_chunks table for parsed BRD markdown indexing.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0014"
down_revision: Union[str, Sequence[str], None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "brd_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("brd_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_level", sa.String(length=32), nullable=False),
        sa.Column("heading", sa.String(length=512), nullable=True),
        sa.Column("heading_depth", sa.Integer(), nullable=True),
        sa.Column("section_path", sa.String(length=1024), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["brd_id"], ["brd_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brd_id", "chunk_index", name="uq_brd_chunks_brd_chunk_index"),
    )
    op.create_index("ix_brd_chunks_brd_id", "brd_chunks", ["brd_id"])
    op.create_index("ix_brd_chunks_user_id", "brd_chunks", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_brd_chunks_user_id", table_name="brd_chunks")
    op.drop_index("ix_brd_chunks_brd_id", table_name="brd_chunks")
    op.drop_table("brd_chunks")
