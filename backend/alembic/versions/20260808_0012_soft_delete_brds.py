"""Add soft-delete (deleted_at) for BRDs with partial unique name index.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, Sequence[str], None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "brd_documents",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_brd_documents_deleted_at",
        "brd_documents",
        ["deleted_at"],
    )
    op.execute("DROP INDEX IF EXISTS ix_brd_documents_user_id_name_lower")
    op.execute(
        """
        CREATE UNIQUE INDEX ix_brd_documents_user_id_name_lower_active
        ON brd_documents (user_id, lower(name))
        WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_brd_documents_user_id_name_lower_active")
    op.execute(
        """
        CREATE UNIQUE INDEX ix_brd_documents_user_id_name_lower
        ON brd_documents (user_id, lower(name))
        """
    )
    op.drop_index("ix_brd_documents_deleted_at", table_name="brd_documents")
    op.drop_column("brd_documents", "deleted_at")
