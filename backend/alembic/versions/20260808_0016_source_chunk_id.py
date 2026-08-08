"""Add source_chunk_id provenance on AI artifacts.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, Sequence[str], None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("brd_features", "brd_sub_features", "brd_stories", "brd_test_cases")


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column("source_chunk_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            f"fk_{table}_source_chunk_id",
            table,
            "brd_chunks",
            ["source_chunk_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            f"ix_{table}_source_chunk_id",
            table,
            ["source_chunk_id"],
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.drop_index(f"ix_{table}_source_chunk_id", table_name=table)
        op.drop_constraint(f"fk_{table}_source_chunk_id", table, type_="foreignkey")
        op.drop_column(table, "source_chunk_id")
