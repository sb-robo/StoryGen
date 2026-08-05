from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.brd_sub_feature import BrdSubFeature, ReviewStatus


class SubFeatureRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, sub_feature: BrdSubFeature) -> BrdSubFeature:
        self.db.add(sub_feature)
        await self.db.flush()
        await self.db.refresh(sub_feature)
        return sub_feature

    async def create_many(self, items: list[BrdSubFeature]) -> list[BrdSubFeature]:
        for item in items:
            self.db.add(item)
        await self.db.flush()
        for item in items:
            await self.db.refresh(item)
        return items

    async def get_by_id(self, sub_feature_id: int) -> BrdSubFeature | None:
        result = await self.db.execute(
            select(BrdSubFeature).where(BrdSubFeature.id == sub_feature_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(
        self, sub_feature_id: int, user_id: int
    ) -> BrdSubFeature | None:
        result = await self.db.execute(
            select(BrdSubFeature).where(
                BrdSubFeature.id == sub_feature_id,
                BrdSubFeature.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    def _filtered_query(
        self,
        user_id: int,
        feature_id: int,
        *,
        status: str | None = None,
    ) -> Select:
        query = select(BrdSubFeature).where(
            BrdSubFeature.user_id == user_id,
            BrdSubFeature.feature_id == feature_id,
        )
        if status:
            query = query.where(BrdSubFeature.status == status)
        return query

    async def list_for_feature(
        self,
        user_id: int,
        feature_id: int,
        *,
        status: str | None = None,
    ) -> list[BrdSubFeature]:
        query = self._filtered_query(user_id, feature_id, status=status)
        result = await self.db.execute(
            query.order_by(BrdSubFeature.sort_order.asc(), BrdSubFeature.id.asc())
        )
        return list(result.scalars().all())

    async def delete_non_finalized_for_feature(self, feature_id: int) -> None:
        await self.db.execute(
            delete(BrdSubFeature).where(
                BrdSubFeature.feature_id == feature_id,
                BrdSubFeature.status.in_(
                    [ReviewStatus.DRAFT.value, ReviewStatus.PENDING_REVIEW.value]
                ),
            )
        )
        await self.db.flush()

    async def update(self, sub_feature: BrdSubFeature) -> BrdSubFeature:
        self.db.add(sub_feature)
        await self.db.flush()
        await self.db.refresh(sub_feature)
        return sub_feature
