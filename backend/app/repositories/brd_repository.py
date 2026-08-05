from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.brd_document import BrdDocument


class BrdRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, brd: BrdDocument) -> BrdDocument:
        self.db.add(brd)
        await self.db.flush()
        await self.db.refresh(brd)
        return brd

    async def get_by_id(self, brd_id: int) -> BrdDocument | None:
        result = await self.db.execute(select(BrdDocument).where(BrdDocument.id == brd_id))
        return result.scalar_one_or_none()

    async def get_by_id_for_user(self, brd_id: int, user_id: int) -> BrdDocument | None:
        result = await self.db.execute(
            select(BrdDocument).where(
                BrdDocument.id == brd_id,
                BrdDocument.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
        search: str | None = None,
    ) -> list[BrdDocument]:
        query = select(BrdDocument).where(BrdDocument.user_id == user_id)
        if status:
            query = query.where(BrdDocument.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    BrdDocument.name.ilike(pattern),
                    BrdDocument.original_filename.ilike(pattern),
                    BrdDocument.file_extension.ilike(pattern),
                )
            )
        result = await self.db.execute(
            query.order_by(BrdDocument.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def count_for_user(
        self,
        user_id: int,
        *,
        status: str | None = None,
        search: str | None = None,
    ) -> int:
        query = select(func.count()).select_from(BrdDocument).where(
            BrdDocument.user_id == user_id
        )
        if status:
            query = query.where(BrdDocument.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    BrdDocument.name.ilike(pattern),
                    BrdDocument.original_filename.ilike(pattern),
                    BrdDocument.file_extension.ilike(pattern),
                )
            )
        result = await self.db.execute(query)
        return result.scalar_one()

    async def update(self, brd: BrdDocument) -> BrdDocument:
        self.db.add(brd)
        await self.db.flush()
        await self.db.refresh(brd)
        return brd

    async def delete(self, brd: BrdDocument) -> None:
        await self.db.execute(delete(BrdDocument).where(BrdDocument.id == brd.id))
        await self.db.flush()
