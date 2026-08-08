from datetime import datetime, timezone

from sqlalchemy import Select, delete, func, or_, select
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

    async def get_by_id_for_user(
        self,
        brd_id: int,
        user_id: int,
        *,
        include_deleted: bool = False,
    ) -> BrdDocument | None:
        query = select(BrdDocument).where(
            BrdDocument.id == brd_id,
            BrdDocument.user_id == user_id,
        )
        if not include_deleted:
            query = query.where(BrdDocument.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def find_by_name_for_user(
        self, user_id: int, name: str, *, exclude_id: int | None = None
    ) -> BrdDocument | None:
        query = select(BrdDocument).where(
            BrdDocument.user_id == user_id,
            BrdDocument.deleted_at.is_(None),
            func.lower(BrdDocument.name) == name.strip().lower(),
        )
        if exclude_id is not None:
            query = query.where(BrdDocument.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def find_by_original_filename_for_user(
        self, user_id: int, original_filename: str
    ) -> BrdDocument | None:
        result = await self.db.execute(
            select(BrdDocument).where(
                BrdDocument.user_id == user_id,
                BrdDocument.deleted_at.is_(None),
                func.lower(BrdDocument.original_filename)
                == original_filename.strip().lower(),
            )
        )
        return result.scalar_one_or_none()

    def _filtered_query(
        self,
        user_id: int,
        *,
        status: str | None = None,
        search: str | None = None,
        file_extension: str | None = None,
        has_images: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        trashed: bool = False,
    ) -> Select:
        query = select(BrdDocument).where(BrdDocument.user_id == user_id)
        if trashed:
            query = query.where(BrdDocument.deleted_at.is_not(None))
        else:
            query = query.where(BrdDocument.deleted_at.is_(None))
        if status:
            query = query.where(BrdDocument.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    BrdDocument.name.ilike(pattern),
                    BrdDocument.original_filename.ilike(pattern),
                )
            )
        if file_extension:
            query = query.where(BrdDocument.file_extension == file_extension.lower())
        if has_images is True:
            query = query.where(BrdDocument.image_count > 0)
        elif has_images is False:
            query = query.where(BrdDocument.image_count == 0)
        if created_from is not None:
            query = query.where(BrdDocument.created_at >= created_from)
        if created_to is not None:
            query = query.where(BrdDocument.created_at <= created_to)
        return query

    async def list_for_user(
        self,
        user_id: int,
        *,
        offset: int,
        limit: int,
        status: str | None = None,
        search: str | None = None,
        file_extension: str | None = None,
        has_images: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        trashed: bool = False,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[BrdDocument]:
        query = self._filtered_query(
            user_id,
            status=status,
            search=search,
            file_extension=file_extension,
            has_images=has_images,
            created_from=created_from,
            created_to=created_to,
            trashed=trashed,
        )
        sort_column = {
            "created_at": BrdDocument.created_at,
            "updated_at": BrdDocument.updated_at,
            "name": BrdDocument.name,
            "file_size_bytes": BrdDocument.file_size_bytes,
            "status": BrdDocument.status,
            "original_filename": BrdDocument.original_filename,
        }.get(sort_by, BrdDocument.created_at)

        order_expr = sort_column.asc() if sort_order == "asc" else sort_column.desc()
        result = await self.db.execute(
            query.order_by(order_expr, BrdDocument.id.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count_for_user(
        self,
        user_id: int,
        *,
        status: str | None = None,
        search: str | None = None,
        file_extension: str | None = None,
        has_images: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        trashed: bool = False,
    ) -> int:
        base = self._filtered_query(
            user_id,
            status=status,
            search=search,
            file_extension=file_extension,
            has_images=has_images,
            created_from=created_from,
            created_to=created_to,
            trashed=trashed,
        )
        result = await self.db.execute(select(func.count()).select_from(base.subquery()))
        return result.scalar_one()

    async def update(self, brd: BrdDocument) -> BrdDocument:
        self.db.add(brd)
        await self.db.flush()
        await self.db.refresh(brd)
        return brd

    async def soft_delete(self, brd: BrdDocument) -> BrdDocument:
        brd.deleted_at = datetime.now(timezone.utc)
        return await self.update(brd)

    async def restore(self, brd: BrdDocument) -> BrdDocument:
        brd.deleted_at = None
        return await self.update(brd)

    async def delete(self, brd: BrdDocument) -> None:
        await self.db.execute(delete(BrdDocument).where(BrdDocument.id == brd.id))
        await self.db.flush()
