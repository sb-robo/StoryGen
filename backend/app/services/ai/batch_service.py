from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.brd_feature import BrdFeature, FeatureStatus
from app.db.models.brd_story import BrdStory, StoryReviewStatus
from app.db.models.brd_sub_feature import BrdSubFeature, ReviewStatus
from app.repositories.brd_repository import BrdRepository
from app.schemas.batch_schema import BatchOperationResponse, BatchSkippedItem
from app.schemas.operation_schema import OperationResponse
from app.services.ai.story_points_service import StoryPointsService
from app.services.ai.story_service import StoryService
from app.services.ai.sub_feature_service import SubFeatureService
from app.services.ai.test_case_service import TestCaseService


class BatchService:
    """Fan-out generate/estimate enqueue across approved parents for a BRD."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.brd_repo = BrdRepository(db)
        self.sub_feature_service = SubFeatureService(db)
        self.story_service = StoryService(db)
        self.story_points_service = StoryPointsService(db)
        self.test_case_service = TestCaseService(db)

    async def _ensure_owned_brd(self, user_id: int, brd_id: int) -> None:
        brd = await self.brd_repo.get_by_id_for_user(brd_id, user_id)
        if not brd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BRD not found",
            )

    async def enqueue_sub_features_all(
        self, user_id: int, brd_id: int
    ) -> tuple[BatchOperationResponse, list[str]]:
        await self._ensure_owned_brd(user_id, brd_id)
        result = await self.db.execute(
            select(BrdFeature).where(
                BrdFeature.user_id == user_id,
                BrdFeature.brd_id == brd_id,
                BrdFeature.status == FeatureStatus.APPROVED.value,
            )
        )
        features = list(result.scalars().all())
        return await self._fan_out(
            brd_id=brd_id,
            action="sub_features",
            resource_type="feature",
            items=features,
            enqueue=lambda item: self.sub_feature_service.enqueue_generation(
                user_id, item.id
            ),
        )

    async def enqueue_stories_all(
        self, user_id: int, brd_id: int
    ) -> tuple[BatchOperationResponse, list[str]]:
        await self._ensure_owned_brd(user_id, brd_id)
        result = await self.db.execute(
            select(BrdSubFeature)
            .join(BrdFeature, BrdFeature.id == BrdSubFeature.feature_id)
            .where(
                BrdSubFeature.user_id == user_id,
                BrdFeature.brd_id == brd_id,
                BrdSubFeature.status == ReviewStatus.APPROVED.value,
            )
        )
        sub_features = list(result.scalars().all())
        return await self._fan_out(
            brd_id=brd_id,
            action="stories",
            resource_type="sub_feature",
            items=sub_features,
            enqueue=lambda item: self.story_service.enqueue_generation(
                user_id, item.id
            ),
        )

    async def enqueue_points_all(
        self, user_id: int, brd_id: int
    ) -> tuple[BatchOperationResponse, list[str]]:
        await self._ensure_owned_brd(user_id, brd_id)
        result = await self.db.execute(
            select(BrdStory)
            .join(BrdSubFeature, BrdSubFeature.id == BrdStory.sub_feature_id)
            .join(BrdFeature, BrdFeature.id == BrdSubFeature.feature_id)
            .where(
                BrdStory.user_id == user_id,
                BrdFeature.brd_id == brd_id,
                BrdStory.status == StoryReviewStatus.APPROVED.value,
            )
        )
        stories = [
            s
            for s in result.scalars().all()
            if s.story_points is None and s.points_status != "approved"
        ]
        return await self._fan_out(
            brd_id=brd_id,
            action="points",
            resource_type="story",
            items=stories,
            enqueue=lambda item: self.story_points_service.enqueue_estimation(
                user_id, item.id
            ),
        )

    async def enqueue_test_cases_all(
        self, user_id: int, brd_id: int
    ) -> tuple[BatchOperationResponse, list[str]]:
        await self._ensure_owned_brd(user_id, brd_id)
        result = await self.db.execute(
            select(BrdStory)
            .join(BrdSubFeature, BrdSubFeature.id == BrdStory.sub_feature_id)
            .join(BrdFeature, BrdFeature.id == BrdSubFeature.feature_id)
            .where(
                BrdStory.user_id == user_id,
                BrdFeature.brd_id == brd_id,
                BrdStory.status == StoryReviewStatus.APPROVED.value,
            )
        )
        stories = list(result.scalars().all())
        return await self._fan_out(
            brd_id=brd_id,
            action="test_cases",
            resource_type="story",
            items=stories,
            enqueue=lambda item: self.test_case_service.enqueue_generation(
                user_id, item.id
            ),
        )

    async def _fan_out(
        self,
        *,
        brd_id: int,
        action: str,
        resource_type: str,
        items: list,
        enqueue,
    ) -> tuple[BatchOperationResponse, list[str]]:
        operations: list[OperationResponse] = []
        skipped: list[BatchSkippedItem] = []
        operation_ids: list[str] = []

        for item in items:
            try:
                op = await enqueue(item)
                operations.append(op)
                operation_ids.append(op.operation_id)
            except HTTPException as exc:
                if exc.status_code == status.HTTP_409_CONFLICT:
                    skipped.append(
                        BatchSkippedItem(
                            resource_type=resource_type,
                            resource_id=item.id,
                            reason="already_running_or_not_eligible",
                        )
                    )
                    continue
                raise

        return (
            BatchOperationResponse(
                brd_id=brd_id,
                action=action,
                operations=operations,
                total=len(operations),
                skipped=skipped,
            ),
            operation_ids,
        )
