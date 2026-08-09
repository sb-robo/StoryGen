from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.feature_embedding import FeatureEmbedding


@dataclass
class SimilarFeatureEmbeddingRow:
    feature_id: int
    brd_id: int
    brd_name: str
    title: str
    text: str
    distance: float


class FeatureEmbeddingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(
        self,
        *,
        feature_id: int,
        user_id: int,
        brd_id: int,
        brd_name: str,
        title: str,
        text: str,
        embedding: list[float],
    ) -> FeatureEmbedding:
        result = await self.db.execute(
            select(FeatureEmbedding).where(FeatureEmbedding.feature_id == feature_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.user_id = user_id
            existing.brd_id = brd_id
            existing.brd_name = brd_name
            existing.title = title
            existing.text = text
            existing.embedding = embedding
            row = existing
        else:
            row = FeatureEmbedding(
                feature_id=feature_id,
                user_id=user_id,
                brd_id=brd_id,
                brd_name=brd_name,
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
        exclude_brd_id: int | None = None,
        exclude_feature_id: int | None = None,
        max_distance: float | None = None,
    ) -> list[SimilarFeatureEmbeddingRow]:
        distance_expr = FeatureEmbedding.embedding.cosine_distance(embedding)
        query = (
            select(
                FeatureEmbedding.feature_id,
                FeatureEmbedding.brd_id,
                FeatureEmbedding.brd_name,
                FeatureEmbedding.title,
                FeatureEmbedding.text,
                distance_expr.label("distance"),
            )
            .where(FeatureEmbedding.user_id == user_id)
            .order_by(distance_expr)
            .limit(limit)
        )
        if exclude_brd_id is not None:
            query = query.where(FeatureEmbedding.brd_id != exclude_brd_id)
        if exclude_feature_id is not None:
            query = query.where(FeatureEmbedding.feature_id != exclude_feature_id)
        if max_distance is not None:
            query = query.where(distance_expr <= max_distance)

        result = await self.db.execute(query)
        rows = result.all()
        return [
            SimilarFeatureEmbeddingRow(
                feature_id=row.feature_id,
                brd_id=row.brd_id,
                brd_name=row.brd_name,
                title=row.title,
                text=row.text,
                distance=float(row.distance),
            )
            for row in rows
        ]
