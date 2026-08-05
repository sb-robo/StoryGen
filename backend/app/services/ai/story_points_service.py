from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.story_points import estimate_story_points
from app.ai.openai_client import OpenAIClient
from app.db.models.async_operation import AsyncOperation, OperationStatus, OperationType
from app.db.models.brd_story import BrdStory, PointsStatus, StoryReviewStatus
from app.repositories.feature_repository import FeatureRepository
from app.repositories.operation_repository import OperationRepository
from app.repositories.story_embedding_repository import StoryEmbeddingRepository
from app.repositories.story_repository import StoryRepository, decode_acceptance_criteria
from app.repositories.sub_feature_repository import SubFeatureRepository
from app.schemas.operation_schema import OperationResponse
from app.schemas.story_schema import (
    StoryPointsResultResponse,
    StoryPointsReviewResponse,
    StoryPointsUpdateRequest,
    StoryResponse,
)
from app.services.ai._helpers import ensure_operation_not_running, operation_response
from app.services.ai.story_service import StoryService


class StoryPointsService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        openai_client: OpenAIClient | None = None,
    ):
        self.db = db
        self.story_repo = StoryRepository(db)
        self.sub_feature_repo = SubFeatureRepository(db)
        self.feature_repo = FeatureRepository(db)
        self.operation_repo = OperationRepository(db)
        self.embedding_repo = StoryEmbeddingRepository(db)
        self.openai_client = openai_client or OpenAIClient(db)
        self._story_service = StoryService(db, openai_client=self.openai_client)

    async def _get_owned_story(self, user_id: int, story_id: int) -> BrdStory:
        story = await self.story_repo.get_by_id_for_user(story_id, user_id)
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found",
            )
        return story

    async def _brd_id_for_story(self, story: BrdStory) -> int:
        sub_feature = await self.sub_feature_repo.get_by_id(story.sub_feature_id)
        if not sub_feature:
            raise RuntimeError("Sub-feature not found for story")
        feature = await self.feature_repo.get_by_id(sub_feature.feature_id)
        if not feature:
            raise RuntimeError("Feature not found for story")
        return feature.brd_id

    async def enqueue_estimation(self, user_id: int, story_id: int) -> OperationResponse:
        story = await self._get_owned_story(user_id, story_id)
        if story.status != StoryReviewStatus.APPROVED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Story must be approved before estimating points.",
            )
        if not self.openai_client.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OPENAI_API_KEY is not configured on the server.",
            )

        await ensure_operation_not_running(
            self.operation_repo,
            user_id=user_id,
            operation_type=OperationType.STORY_POINT_ESTIMATION.value,
            resource_type="story",
            resource_id=story_id,
            conflict_message="Story point estimation is already running for this story.",
        )

        operation = await self.operation_repo.create(
            AsyncOperation(
                user_id=user_id,
                operation_type=OperationType.STORY_POINT_ESTIMATION.value,
                status=OperationStatus.PENDING.value,
                resource_type="story",
                resource_id=story_id,
            )
        )
        await self.db.commit()
        return operation_response(operation)

    async def complete_estimation(self, operation_id: str) -> BrdStory | None:
        operation = await self.operation_repo.get_by_id(operation_id)
        if not operation or operation.resource_id is None:
            return None

        story = await self.story_repo.get_by_id(operation.resource_id)
        if not story:
            return None

        brd_id = await self._brd_id_for_story(story)
        ac = decode_acceptance_criteria(story.acceptance_criteria)

        estimate = await estimate_story_points(
            self.openai_client,
            self.db,
            user_id=operation.user_id,
            story_id=story.id,
            brd_id=brd_id,
            title=story.title,
            description=story.description,
            acceptance_criteria=ac,
            operation_id=operation_id,
        )

        story.story_points = estimate.story_points
        story.points_rationale = estimate.rationale.strip()
        story.points_status = PointsStatus.PENDING_REVIEW.value
        story.points_reviewed_by = None
        story.points_reviewed_at = None
        return await self.story_repo.update(story)

    async def get_estimation_result(
        self, user_id: int, operation_id: str
    ) -> StoryPointsResultResponse:
        operation = await self.operation_repo.get_by_id_for_user(operation_id, user_id)
        if not operation or operation.resource_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation not found",
            )
        if operation.operation_type != OperationType.STORY_POINT_ESTIMATION.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation is not a story point estimation",
            )

        story = await self._get_owned_story(user_id, operation.resource_id)
        if story.story_points is None or story.points_rationale is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story points not available for this operation",
            )

        return StoryPointsResultResponse.build(
            story_id=story.id,
            operation_id=operation_id,
            story_points=story.story_points,
            points_rationale=story.points_rationale,
            points_status=story.points_status or PointsStatus.PENDING_REVIEW.value,
        )

    async def update_points(
        self, user_id: int, story_id: int, payload: StoryPointsUpdateRequest
    ) -> StoryResponse:
        story = await self._get_owned_story(user_id, story_id)
        if story.points_status != PointsStatus.PENDING_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Story points can only be overridden while pending_review.",
            )

        story.story_points = payload.story_points
        if payload.points_rationale is not None:
            story.points_rationale = payload.points_rationale.strip()

        story = await self.story_repo.update(story)
        return self._story_service._to_response(story)

    async def approve_points(
        self, user_id: int, story_id: int
    ) -> StoryPointsReviewResponse:
        story = await self._get_owned_story(user_id, story_id)
        if story.points_status != PointsStatus.PENDING_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Story points must be pending_review to approve.",
            )
        if story.story_points is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Story has no points to approve.",
            )

        story.points_status = PointsStatus.APPROVED.value
        story.points_reviewed_by = user_id
        story.points_reviewed_at = datetime.now(timezone.utc)
        story = await self.story_repo.update(story)

        ac = decode_acceptance_criteria(story.acceptance_criteria)
        ac_text = "\n".join(f"- {c}" for c in ac)
        embed_text = f"{story.title}\n{story.description}\n{ac_text}".strip()
        embedding = await self.openai_client.embed_text(embed_text)
        await self.embedding_repo.upsert(
            story_id=story.id,
            user_id=user_id,
            story_points=story.story_points,
            title=story.title,
            text=embed_text,
            embedding=embedding,
        )

        return StoryPointsReviewResponse(
            id=story.id,
            story_points=story.story_points,
            points_status=story.points_status,
            points_reviewed_by=story.points_reviewed_by,
            points_reviewed_at=story.points_reviewed_at,
        )
