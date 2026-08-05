from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.brd_test_case import BrdTestCase, TestCaseStatus


class TestCaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_many(self, items: list[BrdTestCase]) -> list[BrdTestCase]:
        for item in items:
            self.db.add(item)
        await self.db.flush()
        for item in items:
            await self.db.refresh(item)
        return items

    async def get_by_id(self, test_case_id: int) -> BrdTestCase | None:
        result = await self.db.execute(
            select(BrdTestCase).where(BrdTestCase.id == test_case_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(
        self, test_case_id: int, user_id: int
    ) -> BrdTestCase | None:
        result = await self.db.execute(
            select(BrdTestCase).where(
                BrdTestCase.id == test_case_id,
                BrdTestCase.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    def _filtered_query(
        self,
        user_id: int,
        story_id: int,
        *,
        status: str | None = None,
    ) -> Select:
        query = select(BrdTestCase).where(
            BrdTestCase.user_id == user_id,
            BrdTestCase.story_id == story_id,
        )
        if status:
            query = query.where(BrdTestCase.status == status)
        return query

    async def list_for_story(
        self,
        user_id: int,
        story_id: int,
        *,
        status: str | None = None,
    ) -> list[BrdTestCase]:
        query = self._filtered_query(user_id, story_id, status=status)
        result = await self.db.execute(
            query.order_by(BrdTestCase.sort_order.asc(), BrdTestCase.id.asc())
        )
        return list(result.scalars().all())

    async def delete_non_finalized_for_story(self, story_id: int) -> None:
        await self.db.execute(
            delete(BrdTestCase).where(
                BrdTestCase.story_id == story_id,
                BrdTestCase.status.in_(
                    [TestCaseStatus.DRAFT.value, TestCaseStatus.PENDING_REVIEW.value]
                ),
            )
        )
        await self.db.flush()

    async def update(self, test_case: BrdTestCase) -> BrdTestCase:
        self.db.add(test_case)
        await self.db.flush()
        await self.db.refresh(test_case)
        return test_case
