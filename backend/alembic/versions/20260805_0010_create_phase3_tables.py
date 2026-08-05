"""Phase 3: test cases, story points review fields, pgvector embeddings

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column("brd_stories", sa.Column("points_status", sa.String(length=32), nullable=True))
    op.add_column("brd_stories", sa.Column("points_reviewed_by", sa.Integer(), nullable=True))
    op.add_column(
        "brd_stories",
        sa.Column("points_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_brd_stories_points_reviewed_by",
        "brd_stories",
        "users",
        ["points_reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "brd_test_cases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("story_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("operation_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("steps", sa.Text(), nullable=False),
        sa.Column("expected_result", sa.Text(), nullable=False),
        sa.Column("test_type", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["story_id"], ["brd_stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["operation_id"], ["async_operations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brd_test_cases_story_id", "brd_test_cases", ["story_id"])
    op.create_index("ix_brd_test_cases_user_id", "brd_test_cases", ["user_id"])
    op.create_index("ix_brd_test_cases_status", "brd_test_cases", ["status"])

    op.create_table(
        "story_embeddings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("story_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("story_points", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["story_id"], ["brd_stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("story_id"),
    )
    op.create_index("ix_story_embeddings_user_id", "story_embeddings", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_story_embeddings_user_id", table_name="story_embeddings")
    op.drop_table("story_embeddings")
    op.drop_index("ix_brd_test_cases_status", table_name="brd_test_cases")
    op.drop_index("ix_brd_test_cases_user_id", table_name="brd_test_cases")
    op.drop_index("ix_brd_test_cases_story_id", table_name="brd_test_cases")
    op.drop_table("brd_test_cases")
    op.drop_constraint("fk_brd_stories_points_reviewed_by", "brd_stories", type_="foreignkey")
    op.drop_column("brd_stories", "points_reviewed_at")
    op.drop_column("brd_stories", "points_reviewed_by")
    op.drop_column("brd_stories", "points_status")
