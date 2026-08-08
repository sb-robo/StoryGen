from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.sub_feature_generation import generate_sub_features_from_feature
from app.ai.feature_extraction.chunk_link import resolve_source_chunk_id
from app.ai.openai_client import OpenAIClient
from app.db.models.async_operation import AsyncOperation, OperationStatus, OperationType
from app.db.models.brd_feature import BrdFeature, FeatureStatus
from app.db.models.brd_sub_feature import BrdSubFeature, ReviewStatus
from app.repositories.brd_chunk_repository import BrdChunkRepository
from app.repositories.brd_repository import BrdRepository
from app.repositories.feature_repository import (
    FeatureRepository,
    decode_clarifying_answers,
    decode_clarifying_questions,
    format_clarifying_qa_for_prompt,
)
from app.repositories.operation_repository import OperationRepository
from app.repositories.sub_feature_repository import SubFeatureRepository
from app.schemas.operation_schema import OperationResponse
from app.schemas.pipeline_settings_schema import format_pipeline_context
from app.schemas.sub_feature_schema import (
    SubFeatureGenerationResultResponse,
    SubFeatureListResponse,
    SubFeatureResponse,
    SubFeatureReviewResponse,
    SubFeatureUpdateRequest,
)
from app.services.ai._chunk_context import fetch_brd_chunk_context
from app.services.ai._helpers import ensure_operation_not_running, operation_response


class SubFeatureService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        openai_client: OpenAIClient | None = None,
    ):
        self.db = db
        self.repo = SubFeatureRepository(db)
        self.feature_repo = FeatureRepository(db)
        self.brd_repo = BrdRepository(db)
        self.chunk_repo = BrdChunkRepository(db)
        self.operation_repo = OperationRepository(db)
        self.openai_client = openai_client or OpenAIClient(db)

    def _to_response(self, item: BrdSubFeature) -> SubFeatureResponse:
        return SubFeatureResponse(
            id=item.id,
            feature_id=item.feature_id,
            user_id=item.user_id,
            operation_id=item.operation_id,
            title=item.title,
            description=item.description,
            confidence=item.confidence,
            rationale=item.rationale,
            source_excerpt=item.source_excerpt,
            source_chunk_id=item.source_chunk_id,
            status=item.status,
            reviewed_by=item.reviewed_by,
            reviewed_at=item.reviewed_at,
            sort_order=item.sort_order,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    async def _get_owned_feature(self, user_id: int, feature_id: int) -> BrdFeature:
        feature = await self.feature_repo.get_by_id_for_user(feature_id, user_id)
        if not feature:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feature not found",
            )
        return feature

    async def _get_owned_sub_feature(
        self, user_id: int, sub_feature_id: int
    ) -> BrdSubFeature:
        item = await self.repo.get_by_id_for_user(sub_feature_id, user_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sub-feature not found",
            )
        return item

    async def enqueue_generation(
        self, user_id: int, feature_id: int
    ) -> OperationResponse:
        feature = await self._get_owned_feature(user_id, feature_id)
        if feature.status != FeatureStatus.APPROVED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Feature must be approved before generating sub-features.",
            )
        if not self.openai_client.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OPENAI_API_KEY is not configured on the server.",
            )

        await ensure_operation_not_running(
            self.operation_repo,
            user_id=user_id,
            operation_type=OperationType.SUB_FEATURE_GENERATION.value,
            resource_type="feature",
            resource_id=feature_id,
            conflict_message="Sub-feature generation is already running for this feature.",
        )

        operation = await self.operation_repo.create(
            AsyncOperation(
                user_id=user_id,
                operation_type=OperationType.SUB_FEATURE_GENERATION.value,
                status=OperationStatus.PENDING.value,
                resource_type="feature",
                resource_id=feature_id,
            )
        )
        await self.db.commit()
        return operation_response(operation)

    async def complete_generation(
        self, operation_id: str
    ) -> list[BrdSubFeature] | None:
        operation = await self.operation_repo.get_by_id(operation_id)
        if not operation or operation.resource_id is None:
            return None

        feature = await self.feature_repo.get_by_id(operation.resource_id)
        if not feature:
            return None

        brd = await self.brd_repo.get_by_id(feature.brd_id)
        brd_context = await fetch_brd_chunk_context(
            self.openai_client,
            self.chunk_repo,
            brd_id=feature.brd_id,
            query_parts=[
                feature.title,
                feature.description,
                feature.source_excerpt,
            ],
        )
        output = await generate_sub_features_from_feature(
            self.openai_client,
            feature_title=feature.title,
            feature_description=feature.description,
            source_excerpt=feature.source_excerpt,
            clarifying_qa=format_clarifying_qa_for_prompt(
                decode_clarifying_questions(feature.clarifying_questions),
                decode_clarifying_answers(feature.clarifying_answers),
            ),
            brd_context=brd_context,
            pipeline_context=format_pipeline_context(
                brd.pipeline_settings if brd else None, for_stage="sub_features"
            ),
            operation_id=operation_id,
            user_id=operation.user_id,
            brd_id=feature.brd_id,
        )

        await self.repo.delete_non_finalized_for_feature(feature.id)
        chunks = await self.chunk_repo.list_for_brd(feature.brd_id)

        items: list[BrdSubFeature] = []
        for idx, item in enumerate(output.sub_features):
            items.append(
                BrdSubFeature(
                    feature_id=feature.id,
                    user_id=operation.user_id,
                    operation_id=operation_id,
                    title=item.title.strip(),
                    description=item.description.strip(),
                    confidence=item.confidence,
                    rationale=item.rationale.strip(),
                    source_excerpt=item.source_excerpt,
                    source_chunk_id=resolve_source_chunk_id(
                        chunks,
                        section_path=item.source_section_path,
                        source_excerpt=item.source_excerpt,
                    ),
                    status=ReviewStatus.PENDING_REVIEW.value,
                    sort_order=idx,
                )
            )

        if not items:
            raise RuntimeError("Sub-feature generation returned no items")

        return await self.repo.create_many(items)

    async def list_sub_features(
        self,
        user_id: int,
        feature_id: int,
        *,
        status_filter: str | None = None,
    ) -> SubFeatureListResponse:
        await self._get_owned_feature(user_id, feature_id)
        items = await self.repo.list_for_feature(
            user_id, feature_id, status=status_filter
        )
        return SubFeatureListResponse.build(
            feature_id=feature_id,
            items=[self._to_response(item) for item in items],
        )

    async def get_generation_result(
        self, user_id: int, operation_id: str
    ) -> SubFeatureGenerationResultResponse:
        operation = await self.operation_repo.get_by_id_for_user(operation_id, user_id)
        if not operation or operation.resource_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation not found",
            )
        if operation.operation_type != OperationType.SUB_FEATURE_GENERATION.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation is not a sub-feature generation",
            )

        items = await self.repo.list_for_feature(user_id, operation.resource_id)
        matched = [i for i in items if i.operation_id == operation_id]
        return SubFeatureGenerationResultResponse.build(
            feature_id=operation.resource_id,
            operation_id=operation_id,
            sub_features=[self._to_response(item) for item in matched],
        )

    async def update_sub_feature(
        self, user_id: int, sub_feature_id: int, payload: SubFeatureUpdateRequest
    ) -> SubFeatureResponse:
        item = await self._get_owned_sub_feature(user_id, sub_feature_id)
        if item.status not in {
            ReviewStatus.DRAFT.value,
            ReviewStatus.PENDING_REVIEW.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft or pending_review sub-features can be edited.",
            )

        if payload.title is not None:
            item.title = payload.title.strip()
        if payload.description is not None:
            item.description = payload.description.strip()

        item = await self.repo.update(item)
        return self._to_response(item)

    async def approve_sub_feature(
        self, user_id: int, sub_feature_id: int
    ) -> SubFeatureReviewResponse:
        item = await self._get_owned_sub_feature(user_id, sub_feature_id)
        if item.status != ReviewStatus.PENDING_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending_review sub-features can be approved.",
            )
        item.status = ReviewStatus.APPROVED.value
        item.reviewed_by = user_id
        item.reviewed_at = datetime.now(timezone.utc)
        item = await self.repo.update(item)
        return SubFeatureReviewResponse(
            id=item.id,
            status=item.status,
            reviewed_by=item.reviewed_by,
            reviewed_at=item.reviewed_at,
        )

    async def reject_sub_feature(
        self, user_id: int, sub_feature_id: int
    ) -> SubFeatureReviewResponse:
        item = await self._get_owned_sub_feature(user_id, sub_feature_id)
        if item.status != ReviewStatus.PENDING_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending_review sub-features can be rejected.",
            )
        item.status = ReviewStatus.REJECTED.value
        item.reviewed_by = user_id
        item.reviewed_at = datetime.now(timezone.utc)
        item = await self.repo.update(item)
        return SubFeatureReviewResponse(
            id=item.id,
            status=item.status,
            reviewed_by=item.reviewed_by,
            reviewed_at=item.reviewed_at,
        )

    async def reopen_sub_feature(
        self, user_id: int, sub_feature_id: int
    ) -> SubFeatureReviewResponse:
        item = await self._get_owned_sub_feature(user_id, sub_feature_id)
        if item.status != ReviewStatus.REJECTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only rejected sub-features can be reopened.",
            )
        item.status = ReviewStatus.PENDING_REVIEW.value
        item.reviewed_by = None
        item.reviewed_at = None
        item = await self.repo.update(item)
        return SubFeatureReviewResponse(
            id=item.id,
            status=item.status,
            reviewed_by=item.reviewed_by,
            reviewed_at=item.reviewed_at,
        )
