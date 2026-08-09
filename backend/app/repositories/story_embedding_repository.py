from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.story_embedding import StoryEmbedding


@dataclass
class SimilarEmbeddingRow:
    story_id: int
    brd_id: int | None
    brd_name: str | None
    title: str
    story_points: int | None
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
        story_points: int | None,
        title: str,
        text: str,
        embedding: list[float],
        brd_id: int | None = None,
        brd_name: str | None = None,
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
            if brd_id is not None:
                existing.brd_id = brd_id
            if brd_name is not None:
                existing.brd_name = brd_name
            row = existing
        else:
            row = StoryEmbedding(
                story_id=story_id,
                user_id=user_id,
                brd_id=brd_id,
                brd_name=brd_name,
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
        exclude_brd_id: int | None = None,
        require_points: bool = False,
        max_distance: float | None = None,
    ) -> list[SimilarEmbeddingRow]:
        distance_expr = StoryEmbedding.embedding.cosine_distance(embedding)
        query = (
            select(
                StoryEmbedding.story_id,
                StoryEmbedding.brd_id,
                StoryEmbedding.brd_name,
                StoryEmbedding.title,
                StoryEmbedding.story_points,
                StoryEmbedding.text,
                distance_expr.label("distance"),
            )
            .where(StoryEmbedding.user_id == user_id)
            .order_by(distance_expr)
            .limit(limit)
        )
        if exclude_story_id is not None:
            query = query.where(StoryEmbedding.story_id != exclude_story_id)
        if exclude_brd_id is not None:
            query = query.where(StoryEmbedding.brd_id != exclude_brd_id)
        if require_points:
            query = query.where(StoryEmbedding.story_points.is_not(None))
        if max_distance is not None:
            query = query.where(distance_expr <= max_distance)

        result = await self.db.execute(query)
        rows = result.all()
        return [
            SimilarEmbeddingRow(
                story_id=row.story_id,
                brd_id=row.brd_id,
                brd_name=row.brd_name,
                title=row.title,
                story_points=row.story_points,
                text=row.text,
                distance=float(row.distance),
            )
            for row in rows
        ]
