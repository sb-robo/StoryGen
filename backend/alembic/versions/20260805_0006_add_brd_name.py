"""add name column to brd_documents

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "brd_documents",
        sa.Column("name", sa.String(length=255), nullable=False, server_default="Untitled BRD"),
    )
    op.alter_column("brd_documents", "name", server_default=None)


def downgrade() -> None:
    op.drop_column("brd_documents", "name")
