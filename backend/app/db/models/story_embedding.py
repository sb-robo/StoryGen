from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.db.models.base import Base


class StoryEmbedding(Base):
    __tablename__ = "story_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(
        ForeignKey("brd_stories.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    brd_id: Mapped[int | None] = mapped_column(
        ForeignKey("brd_documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    brd_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    story_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.OPENAI_EMBEDDING_DIMENSIONS)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
