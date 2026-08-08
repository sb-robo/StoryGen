from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.brd_chunk import BrdChunk


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

    async def list_for_brd(self, brd_id: int) -> list[BrdChunk]:
        result = await self.db.execute(
            select(BrdChunk)
            .where(BrdChunk.brd_id == brd_id)
            .order_by(BrdChunk.chunk_index.asc())
        )
        return list(result.scalars().all())
