"""add unique index on brd_documents (user_id, lower(name))

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-05

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Functional unique index — enforces uniqueness at the DB level (race-safe),
    # matching the case-insensitive check already done in the application layer.
    op.execute(
        "CREATE UNIQUE INDEX ix_brd_documents_user_id_name_lower "
        "ON brd_documents (user_id, lower(name))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_brd_documents_user_id_name_lower")
