"""Extend brd_chunks with parent links and chunk kind.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: Union[str, Sequence[str], None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "brd_chunks",
        "chunk_level",
        existing_type=sa.String(length=32),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.add_column(
        "brd_chunks",
        sa.Column("chunk_kind", sa.String(length=32), nullable=False, server_default="section"),
    )
    op.add_column(
        "brd_chunks",
        sa.Column("parent_chunk_index", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_brd_chunks_parent_chunk_index",
        "brd_chunks",
        ["brd_id", "parent_chunk_index"],
    )


def downgrade() -> None:
    op.drop_index("ix_brd_chunks_parent_chunk_index", table_name="brd_chunks")
    op.drop_column("brd_chunks", "parent_chunk_index")
    op.drop_column("brd_chunks", "chunk_kind")
