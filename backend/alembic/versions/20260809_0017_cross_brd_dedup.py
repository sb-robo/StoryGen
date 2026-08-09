"""Phase 5 cross-BRD RAG dedup: feature embeddings + story brd scope + UI matches.

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0017"
down_revision: Union[str, Sequence[str], None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.create_table(
        "feature_embeddings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("feature_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("brd_id", sa.Integer(), nullable=False),
        sa.Column("brd_name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["feature_id"], ["brd_features.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brd_id"], ["brd_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feature_id"),
    )
    op.create_index("ix_feature_embeddings_user_id", "feature_embeddings", ["user_id"])
    op.create_index("ix_feature_embeddings_brd_id", "feature_embeddings", ["brd_id"])

    op.add_column(
        "story_embeddings",
        sa.Column("brd_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "story_embeddings",
        sa.Column("brd_name", sa.String(length=255), nullable=True),
    )
    op.create_foreign_key(
        "fk_story_embeddings_brd_id",
        "story_embeddings",
        "brd_documents",
        ["brd_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_story_embeddings_brd_id", "story_embeddings", ["brd_id"])
    op.alter_column(
        "story_embeddings",
        "story_points",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # Backfill brd scope for existing story embeddings (best-effort).
    op.execute(
        """
        UPDATE story_embeddings se
        SET brd_id = bf.brd_id,
            brd_name = bd.name
        FROM brd_stories bs
        JOIN brd_sub_features bsf ON bsf.id = bs.sub_feature_id
        JOIN brd_features bf ON bf.id = bsf.feature_id
        JOIN brd_documents bd ON bd.id = bf.brd_id
        WHERE se.story_id = bs.id
        """
    )

    op.add_column(
        "brd_features",
        sa.Column("cross_brd_similar", JSONB(), nullable=True),
    )
    op.add_column(
        "brd_stories",
        sa.Column("cross_brd_similar", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("brd_stories", "cross_brd_similar")
    op.drop_column("brd_features", "cross_brd_similar")

    op.drop_index("ix_story_embeddings_brd_id", table_name="story_embeddings")
    op.drop_constraint(
        "fk_story_embeddings_brd_id", "story_embeddings", type_="foreignkey"
    )
    op.drop_column("story_embeddings", "brd_name")
    op.drop_column("story_embeddings", "brd_id")
    op.alter_column(
        "story_embeddings",
        "story_points",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_index("ix_feature_embeddings_brd_id", table_name="feature_embeddings")
    op.drop_index("ix_feature_embeddings_user_id", table_name="feature_embeddings")
    op.drop_table("feature_embeddings")
