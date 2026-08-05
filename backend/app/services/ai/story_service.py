from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.story_generation import generate_stories_from_sub_feature
from app.ai.openai_client import OpenAIClient
from app.db.models.async_operation import AsyncOperation, OperationStatus, OperationType
from app.db.models.brd_story import BrdStory, StoryReviewStatus
from app.db.models.brd_sub_feature import BrdSubFeature, ReviewStatus
from app.repositories.feature_repository import FeatureRepository
from app.repositories.operation_repository import OperationRepository
from app.repositories.story_repository import (
    StoryRepository,
    decode_acceptance_criteria,
    encode_acceptance_criteria,
)
from app.repositories.sub_feature_repository import SubFeatureRepository
from app.schemas.operation_schema import OperationResponse
from app.schemas.story_schema import (
    StoryGenerationResultResponse,
    StoryListResponse,
    StoryResponse,
    StoryReviewResponse,
    StoryUpdateRequest,
)
from app.services.ai._helpers import ensure_operation_not_running, operation_response


class StoryService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        openai_client: OpenAIClient | None = None,
    ):
        self.db = db
        self.repo = StoryRepository(db)
        self.sub_feature_repo = SubFeatureRepository(db)
        self.feature_repo = FeatureRepository(db)
        self.operation_repo = OperationRepository(db)
        self.openai_client = openai_client or OpenAIClient(db)

    def _to_response(self, item: BrdStory) -> StoryResponse:
        return StoryResponse(
            id=item.id,
            sub_feature_id=item.sub_feature_id,
            user_id=item.user_id,
            operation_id=item.operation_id,
            title=item.title,
            description=item.description,
            acceptance_criteria=decode_acceptance_criteria(item.acceptance_criteria),
            confidence=item.confidence,
            rationale=item.rationale,
            source_excerpt=item.source_excerpt,
            status=item.status,
            story_points=item.story_points,
            points_rationale=item.points_rationale,
            points_status=item.points_status,
            points_reviewed_by=item.points_reviewed_by,
            points_reviewed_at=item.points_reviewed_at,
            reviewed_by=item.reviewed_by,
            reviewed_at=item.reviewed_at,
            sort_order=item.sort_order,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    async def _get_owned_sub_feature(
        self, user_id: int, sub_feature_id: int
    ) -> BrdSubFeature:
        item = await self.sub_feature_repo.get_by_id_for_user(sub_feature_id, user_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sub-feature not found",
            )
        return item

    async def _get_owned_story(self, user_id: int, story_id: int) -> BrdStory:
        item = await self.repo.get_by_id_for_user(story_id, user_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found",
            )
        return item

    async def enqueue_generation(
        self, user_id: int, sub_feature_id: int
    ) -> OperationResponse:
        sub_feature = await self._get_owned_sub_feature(user_id, sub_feature_id)
        if sub_feature.status != ReviewStatus.APPROVED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Sub-feature must be approved before generating stories.",
            )
        if not self.openai_client.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OPENAI_API_KEY is not configured on the server.",
            )

        await ensure_operation_not_running(
            self.operation_repo,
            user_id=user_id,
            operation_type=OperationType.STORY_GENERATION.value,
            resource_type="sub_feature",
            resource_id=sub_feature_id,
            conflict_message="Story generation is already running for this sub-feature.",
        )

        operation = await self.operation_repo.create(
            AsyncOperation(
                user_id=user_id,
                operation_type=OperationType.STORY_GENERATION.value,
                status=OperationStatus.PENDING.value,
                resource_type="sub_feature",
                resource_id=sub_feature_id,
            )
        )
        await self.db.commit()
        return operation_response(operation)

    async def complete_generation(self, operation_id: str) -> list[BrdStory] | None:
        operation = await self.operation_repo.get_by_id(operation_id)
        if not operation or operation.resource_id is None:
            return None

        sub_feature = await self.sub_feature_repo.get_by_id(operation.resource_id)
        if not sub_feature:
            return None

        feature = await self.feature_repo.get_by_id(sub_feature.feature_id)
        if not feature:
            return None

        output = await generate_stories_from_sub_feature(
            self.openai_client,
            feature_title=feature.title,
            feature_description=feature.description,
            sub_feature_title=sub_feature.title,
            sub_feature_description=sub_feature.description,
            source_excerpt=sub_feature.source_excerpt,
            operation_id=operation_id,
            user_id=operation.user_id,
            brd_id=feature.brd_id,
        )

        await self.repo.delete_non_finalized_for_sub_feature(sub_feature.id)

        items: list[BrdStory] = []
        for idx, item in enumerate(output.stories):
            items.append(
                BrdStory(
                    sub_feature_id=sub_feature.id,
                    user_id=operation.user_id,
                    operation_id=operation_id,
                    title=item.title.strip(),
                    description=item.description.strip(),
                    acceptance_criteria=encode_acceptance_criteria(
                        item.acceptance_criteria
                    ),
                    confidence=item.confidence,
                    rationale=item.rationale.strip(),
                    source_excerpt=item.source_excerpt,
                    status=StoryReviewStatus.PENDING_REVIEW.value,
                    sort_order=idx,
                )
            )

        if not items:
            raise RuntimeError("Story generation returned no items")

        return await self.repo.create_many(items)

    async def list_stories(
        self,
        user_id: int,
        sub_feature_id: int,
        *,
        status_filter: str | None = None,
    ) -> StoryListResponse:
        await self._get_owned_sub_feature(user_id, sub_feature_id)
        items = await self.repo.list_for_sub_feature(
            user_id, sub_feature_id, status=status_filter
        )
        return StoryListResponse.build(
            sub_feature_id=sub_feature_id,
            items=[self._to_response(item) for item in items],
        )

    async def get_generation_result(
        self, user_id: int, operation_id: str
    ) -> StoryGenerationResultResponse:
        operation = await self.operation_repo.get_by_id_for_user(operation_id, user_id)
        if not operation or operation.resource_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation not found",
            )
        if operation.operation_type != OperationType.STORY_GENERATION.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation is not a story generation",
            )

        items = await self.repo.list_for_sub_feature(user_id, operation.resource_id)
        matched = [i for i in items if i.operation_id == operation_id]
        return StoryGenerationResultResponse.build(
            sub_feature_id=operation.resource_id,
            operation_id=operation_id,
            stories=[self._to_response(item) for item in matched],
        )

    async def update_story(
        self, user_id: int, story_id: int, payload: StoryUpdateRequest
    ) -> StoryResponse:
        item = await self._get_owned_story(user_id, story_id)
        if item.status not in {
            StoryReviewStatus.DRAFT.value,
            StoryReviewStatus.PENDING_REVIEW.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft or pending_review stories can be edited.",
            )

        if payload.title is not None:
            item.title = payload.title.strip()
        if payload.description is not None:
            item.description = payload.description.strip()
        if payload.acceptance_criteria is not None:
            item.acceptance_criteria = encode_acceptance_criteria(
                payload.acceptance_criteria
            )

        item = await self.repo.update(item)
        return self._to_response(item)

    async def approve_story(self, user_id: int, story_id: int) -> StoryReviewResponse:
        item = await self._get_owned_story(user_id, story_id)
        if item.status != StoryReviewStatus.PENDING_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending_review stories can be approved.",
            )
        item.status = StoryReviewStatus.APPROVED.value
        item.reviewed_by = user_id
        item.reviewed_at = datetime.now(timezone.utc)
        item = await self.repo.update(item)
        return StoryReviewResponse(
            id=item.id,
            status=item.status,
            reviewed_by=item.reviewed_by,
            reviewed_at=item.reviewed_at,
        )

    async def reject_story(self, user_id: int, story_id: int) -> StoryReviewResponse:
        item = await self._get_owned_story(user_id, story_id)
        if item.status != StoryReviewStatus.PENDING_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending_review stories can be rejected.",
            )
        item.status = StoryReviewStatus.REJECTED.value
        item.reviewed_by = user_id
        item.reviewed_at = datetime.now(timezone.utc)
        item = await self.repo.update(item)
        return StoryReviewResponse(
            id=item.id,
            status=item.status,
            reviewed_by=item.reviewed_by,
            reviewed_at=item.reviewed_at,
        )
