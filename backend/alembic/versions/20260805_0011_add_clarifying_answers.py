"""Add clarifying_answers to brd_features for human reviewer responses."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, Sequence[str], None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "brd_features",
        sa.Column("clarifying_answers", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("brd_features", "clarifying_answers")
