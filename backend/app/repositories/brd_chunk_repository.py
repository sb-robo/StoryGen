from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.brd_chunk import BrdChunk


@dataclass
class SimilarChunkRow:
    id: int
    chunk_index: int
    section_path: str
    heading: str | None
    chunk_kind: str
    content: str
    distance: float


class BrdChunkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def delete_for_brd(self, brd_id: int) -> None:
        await self.db.execute(delete(BrdChunk).where(BrdChunk.brd_id == brd_id))

    async def create_many(self, rows: list[BrdChunk]) -> list[BrdChunk]:
        self.db.add_all(rows)
        await self.db.flush()
        return rows

    async def count_for_brd(self, brd_id: int) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(BrdChunk).where(BrdChunk.brd_id == brd_id)
        )
        return int(result.scalar_one())

    async def count_embedded_for_brd(self, brd_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(BrdChunk)
            .where(BrdChunk.brd_id == brd_id)
            .where(BrdChunk.embedding.is_not(None))
        )
        return int(result.scalar_one())

    async def list_for_brd(self, brd_id: int) -> list[BrdChunk]:
        result = await self.db.execute(
            select(BrdChunk)
            .where(BrdChunk.brd_id == brd_id)
            .order_by(BrdChunk.chunk_index.asc())
        )
        return list(result.scalars().all())

    async def find_similar(
        self,
        brd_id: int,
        embedding: list[float],
        *,
        limit: int,
    ) -> list[SimilarChunkRow]:
        """Return top-k chunks for a BRD by cosine distance (lower = more similar)."""
        query = (
            select(
                BrdChunk.id,
                BrdChunk.chunk_index,
                BrdChunk.section_path,
                BrdChunk.heading,
                BrdChunk.chunk_kind,
                BrdChunk.content,
                BrdChunk.embedding.cosine_distance(embedding).label("distance"),
            )
            .where(BrdChunk.brd_id == brd_id)
            .where(BrdChunk.embedding.is_not(None))
            .order_by("distance")
            .limit(limit)
        )
        result = await self.db.execute(query)
        rows = result.all()
        return [
            SimilarChunkRow(
                id=row.id,
                chunk_index=row.chunk_index,
                section_path=row.section_path,
                heading=row.heading,
                chunk_kind=row.chunk_kind,
                content=row.content,
                distance=float(row.distance),
            )
            for row in rows
        ]
