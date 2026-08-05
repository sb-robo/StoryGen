import json

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.brd_story import BrdStory, StoryReviewStatus


class StoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, story: BrdStory) -> BrdStory:
        self.db.add(story)
        await self.db.flush()
        await self.db.refresh(story)
        return story

    async def create_many(self, items: list[BrdStory]) -> list[BrdStory]:
        for item in items:
            self.db.add(item)
        await self.db.flush()
        for item in items:
            await self.db.refresh(item)
        return items

    async def get_by_id(self, story_id: int) -> BrdStory | None:
        result = await self.db.execute(select(BrdStory).where(BrdStory.id == story_id))
        return result.scalar_one_or_none()

    async def get_by_id_for_user(self, story_id: int, user_id: int) -> BrdStory | None:
        result = await self.db.execute(
            select(BrdStory).where(
                BrdStory.id == story_id,
                BrdStory.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    def _filtered_query(
        self,
        user_id: int,
        sub_feature_id: int,
        *,
        status: str | None = None,
    ) -> Select:
        query = select(BrdStory).where(
            BrdStory.user_id == user_id,
            BrdStory.sub_feature_id == sub_feature_id,
        )
        if status:
            query = query.where(BrdStory.status == status)
        return query

    async def list_for_sub_feature(
        self,
        user_id: int,
        sub_feature_id: int,
        *,
        status: str | None = None,
    ) -> list[BrdStory]:
        query = self._filtered_query(user_id, sub_feature_id, status=status)
        result = await self.db.execute(
            query.order_by(BrdStory.sort_order.asc(), BrdStory.id.asc())
        )
        return list(result.scalars().all())

    async def delete_non_finalized_for_sub_feature(self, sub_feature_id: int) -> None:
        await self.db.execute(
            delete(BrdStory).where(
                BrdStory.sub_feature_id == sub_feature_id,
                BrdStory.status.in_(
                    [
                        StoryReviewStatus.DRAFT.value,
                        StoryReviewStatus.PENDING_REVIEW.value,
                    ]
                ),
            )
        )
        await self.db.flush()

    async def update(self, story: BrdStory) -> BrdStory:
        self.db.add(story)
        await self.db.flush()
        await self.db.refresh(story)
        return story


def encode_acceptance_criteria(criteria: list[str] | None) -> str | None:
    if not criteria:
        return None
    return json.dumps(criteria)


def decode_acceptance_criteria(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []
