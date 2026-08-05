"""create brd_features and llm_call_logs tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brd_features",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("brd_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("operation_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("clarifying_questions", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["brd_id"], ["brd_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["operation_id"], ["async_operations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brd_features_brd_id", "brd_features", ["brd_id"])
    op.create_index("ix_brd_features_user_id", "brd_features", ["user_id"])
    op.create_index("ix_brd_features_status", "brd_features", ["status"])

    op.create_table(
        "llm_call_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("operation_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("brd_id", sa.Integer(), nullable=True),
        sa.Column("node_name", sa.String(length=128), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["operation_id"], ["async_operations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brd_id"], ["brd_documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_call_logs_operation_id", "llm_call_logs", ["operation_id"])
    op.create_index("ix_llm_call_logs_user_id", "llm_call_logs", ["user_id"])
    op.create_index("ix_llm_call_logs_brd_id", "llm_call_logs", ["brd_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_call_logs_brd_id", table_name="llm_call_logs")
    op.drop_index("ix_llm_call_logs_user_id", table_name="llm_call_logs")
    op.drop_index("ix_llm_call_logs_operation_id", table_name="llm_call_logs")
    op.drop_table("llm_call_logs")
    op.drop_index("ix_brd_features_status", table_name="brd_features")
    op.drop_index("ix_brd_features_user_id", table_name="brd_features")
    op.drop_index("ix_brd_features_brd_id", table_name="brd_features")
    op.drop_table("brd_features")
