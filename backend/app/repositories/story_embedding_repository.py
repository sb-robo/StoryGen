from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.story_embedding import StoryEmbedding


@dataclass
class SimilarEmbeddingRow:
    title: str
    story_points: int
    text: str
    distance: float


class StoryEmbeddingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(
        self,
        *,
        story_id: int,
        user_id: int,
        story_points: int,
        title: str,
        text: str,
        embedding: list[float],
    ) -> StoryEmbedding:
        result = await self.db.execute(
            select(StoryEmbedding).where(StoryEmbedding.story_id == story_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.story_points = story_points
            existing.title = title
            existing.text = text
            existing.embedding = embedding
            row = existing
        else:
            row = StoryEmbedding(
                story_id=story_id,
                user_id=user_id,
                story_points=story_points,
                title=title,
                text=text,
                embedding=embedding,
            )
            self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def find_similar(
        self,
        user_id: int,
        embedding: list[float],
        *,
        limit: int,
        exclude_story_id: int | None = None,
    ) -> list[SimilarEmbeddingRow]:
        query = (
            select(
                StoryEmbedding.title,
                StoryEmbedding.story_points,
                StoryEmbedding.text,
                StoryEmbedding.embedding.cosine_distance(embedding).label("distance"),
            )
            .where(StoryEmbedding.user_id == user_id)
            .order_by("distance")
            .limit(limit)
        )
        if exclude_story_id is not None:
            query = query.where(StoryEmbedding.story_id != exclude_story_id)

        result = await self.db.execute(query)
        rows = result.all()
        return [
            SimilarEmbeddingRow(
                title=row.title,
                story_points=row.story_points,
                text=row.text,
                distance=float(row.distance),
            )
            for row in rows
        ]
