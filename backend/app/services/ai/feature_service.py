from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.feature_extraction import extract_features_from_brd
from app.ai.openai_client import OpenAIClient
from app.db.models.async_operation import AsyncOperation, OperationStatus, OperationType
from app.db.models.brd_document import BrdStatus
from app.db.models.brd_feature import BrdFeature, FeatureStatus
from app.repositories.brd_repository import BrdRepository
from app.repositories.feature_repository import (
    FeatureRepository,
    decode_clarifying_answers,
    decode_clarifying_questions,
    encode_clarifying_answers,
    encode_clarifying_questions,
)
from app.repositories.operation_repository import OperationRepository
from app.schemas.feature_schema import (
    ClarifyingAnswer,
    FeatureExtractionResultResponse,
    FeatureListResponse,
    FeatureResponse,
    FeatureReviewResponse,
    FeatureUpdateRequest,
)
from app.schemas.operation_schema import OperationResponse
from app.services.brd.storage_service import BrdStorageService


class FeatureService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        openai_client: OpenAIClient | None = None,
        storage: BrdStorageService | None = None,
    ):
        self.db = db
        self.repo = FeatureRepository(db)
        self.brd_repo = BrdRepository(db)
        self.operation_repo = OperationRepository(db)
        self.storage = storage or BrdStorageService()
        self.openai_client = openai_client or OpenAIClient(db)

    def _to_response(self, feature: BrdFeature) -> FeatureResponse:
        return FeatureResponse(
            id=feature.id,
            brd_id=feature.brd_id,
            user_id=feature.user_id,
            operation_id=feature.operation_id,
            title=feature.title,
            description=feature.description,
            confidence=feature.confidence,
            rationale=feature.rationale,
            clarifying_questions=decode_clarifying_questions(feature.clarifying_questions),
            clarifying_answers=[
                ClarifyingAnswer(**item)
                for item in decode_clarifying_answers(feature.clarifying_answers)
            ],
            source_excerpt=feature.source_excerpt,
            status=feature.status,
            reviewed_by=feature.reviewed_by,
            reviewed_at=feature.reviewed_at,
            sort_order=feature.sort_order,
            created_at=feature.created_at,
            updated_at=feature.updated_at,
        )

    def _operation_response(self, operation: AsyncOperation) -> OperationResponse:
        return OperationResponse(
            operation_id=operation.id,
            operation_type=operation.operation_type,
            status=operation.status,
            resource_type=operation.resource_type,
            resource_id=operation.resource_id,
            error_message=operation.error_message,
            created_at=operation.created_at,
            updated_at=operation.updated_at,
            completed_at=operation.completed_at,
        )

    async def _get_owned_brd(self, user_id: int, brd_id: int):
        brd = await self.brd_repo.get_by_id_for_user(brd_id, user_id)
        if not brd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BRD not found",
            )
        return brd

    async def _get_owned_feature(self, user_id: int, feature_id: int) -> BrdFeature:
        feature = await self.repo.get_by_id_for_user(feature_id, user_id)
        if not feature:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feature not found",
            )
        return feature

    async def _ensure_extraction_not_running(self, user_id: int, brd_id: int) -> None:
        ops = await self.operation_repo.list_for_user(
            user_id,
            offset=0,
            limit=1,
            operation_type=OperationType.FEATURE_EXTRACTION.value,
            resource_type="brd",
            resource_id=brd_id,
            status=OperationStatus.RUNNING.value,
        )
        if ops:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Feature extraction is already running for this BRD.",
            )
        pending = await self.operation_repo.list_for_user(
            user_id,
            offset=0,
            limit=1,
            operation_type=OperationType.FEATURE_EXTRACTION.value,
            resource_type="brd",
            resource_id=brd_id,
            status=OperationStatus.PENDING.value,
        )
        if pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Feature extraction is already queued for this BRD.",
            )

    async def enqueue_extraction(self, user_id: int, brd_id: int) -> OperationResponse:
        brd = await self._get_owned_brd(user_id, brd_id)
        if brd.status != BrdStatus.PARSED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="BRD must be parsed before feature extraction.",
            )
        if not self.openai_client.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OPENAI_API_KEY is not configured on the server.",
            )

        await self._ensure_extraction_not_running(user_id, brd_id)

        operation = await self.operation_repo.create(
            AsyncOperation(
                user_id=user_id,
                operation_type=OperationType.FEATURE_EXTRACTION.value,
                status=OperationStatus.PENDING.value,
                resource_type="brd",
                resource_id=brd_id,
            )
        )
        await self.db.commit()
        return self._operation_response(operation)

    async def complete_extraction(self, operation_id: str) -> list[BrdFeature] | None:
        """Background worker entry — no ownership check."""
        operation = await self.operation_repo.get_by_id(operation_id)
        if not operation or operation.resource_id is None:
            return None

        brd = await self.brd_repo.get_by_id(operation.resource_id)
        if not brd:
            return None

        text = await self.storage.read_parsed_markdown(brd.parsed_text_path)
        if not text:
            raise RuntimeError("Parsed BRD content is not available")

        output = await extract_features_from_brd(
            self.openai_client,
            brd_name=brd.name,
            brd_content=text,
            operation_id=operation_id,
            user_id=operation.user_id,
            brd_id=brd.id,
        )

        await self.repo.delete_non_finalized_for_brd(brd.id)

        features: list[BrdFeature] = []
        for idx, item in enumerate(output.features):
            features.append(
                BrdFeature(
                    brd_id=brd.id,
                    user_id=operation.user_id,
                    operation_id=operation_id,
                    title=item.title.strip(),
                    description=item.description.strip(),
                    confidence=item.confidence,
                    rationale=item.rationale.strip(),
                    clarifying_questions=encode_clarifying_questions(
                        item.clarifying_questions
                    ),
                    source_excerpt=item.source_excerpt,
                    status=FeatureStatus.PENDING_REVIEW.value,
                    sort_order=idx,
                )
            )

        if not features:
            raise RuntimeError("Feature extraction returned no features")

        return await self.repo.create_many(features)

    async def list_features(
        self,
        user_id: int,
        brd_id: int,
        *,
        status_filter: str | None = None,
    ) -> FeatureListResponse:
        await self._get_owned_brd(user_id, brd_id)
        items = await self.repo.list_for_brd(
            user_id, brd_id, status=status_filter
        )
        responses = [self._to_response(item) for item in items]
        return FeatureListResponse.build(brd_id=brd_id, items=responses)

    async def get_extraction_result(
        self, user_id: int, operation_id: str
    ) -> FeatureExtractionResultResponse:
        operation = await self.operation_repo.get_by_id_for_user(operation_id, user_id)
        if not operation or operation.resource_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation not found",
            )
        if operation.operation_type != OperationType.FEATURE_EXTRACTION.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation is not a feature extraction",
            )

        features = await self.repo.list_for_brd(user_id, operation.resource_id)
        matched = [f for f in features if f.operation_id == operation_id]
        responses = [self._to_response(item) for item in matched]
        return FeatureExtractionResultResponse.build(
            brd_id=operation.resource_id,
            operation_id=operation_id,
            features=responses,
        )

    async def update_feature(
        self, user_id: int, feature_id: int, payload: FeatureUpdateRequest
    ) -> FeatureResponse:
        feature = await self._get_owned_feature(user_id, feature_id)
        if feature.status == FeatureStatus.REJECTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Rejected features cannot be edited.",
            )

        answers_only = (
            payload.title is None
            and payload.description is None
            and payload.clarifying_questions is None
            and payload.clarifying_answers is not None
        )
        if feature.status == FeatureStatus.APPROVED.value and not answers_only:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Approved features can only be updated with clarifying_answers.",
            )
        if feature.status not in {
            FeatureStatus.DRAFT.value,
            FeatureStatus.PENDING_REVIEW.value,
        } and not answers_only:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft or pending_review features can be edited.",
            )

        if payload.title is not None:
            feature.title = payload.title.strip()
        if payload.description is not None:
            feature.description = payload.description.strip()
        if payload.clarifying_questions is not None:
            feature.clarifying_questions = encode_clarifying_questions(
                payload.clarifying_questions
            )
        if payload.clarifying_answers is not None:
            questions = decode_clarifying_questions(feature.clarifying_questions)
            question_set = set(questions)
            normalized: list[dict[str, str]] = []
            for item in payload.clarifying_answers:
                question = item.question.strip()
                answer = item.answer.strip()
                if question not in question_set:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Unknown clarifying question: {question}",
                    )
                if answer:
                    normalized.append({"question": question, "answer": answer})
            feature.clarifying_answers = encode_clarifying_answers(normalized)

        feature = await self.repo.update(feature)
        return self._to_response(feature)

    async def approve_feature(
        self, user_id: int, feature_id: int
    ) -> FeatureReviewResponse:
        feature = await self._get_owned_feature(user_id, feature_id)
        if feature.status != FeatureStatus.PENDING_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending_review features can be approved.",
            )
        feature.status = FeatureStatus.APPROVED.value
        feature.reviewed_by = user_id
        feature.reviewed_at = datetime.now(timezone.utc)
        feature = await self.repo.update(feature)
        return FeatureReviewResponse(
            id=feature.id,
            status=feature.status,
            reviewed_by=feature.reviewed_by,
            reviewed_at=feature.reviewed_at,
        )

    async def reject_feature(
        self, user_id: int, feature_id: int
    ) -> FeatureReviewResponse:
        feature = await self._get_owned_feature(user_id, feature_id)
        if feature.status != FeatureStatus.PENDING_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending_review features can be rejected.",
            )
        feature.status = FeatureStatus.REJECTED.value
        feature.reviewed_by = user_id
        feature.reviewed_at = datetime.now(timezone.utc)
        feature = await self.repo.update(feature)
        return FeatureReviewResponse(
            id=feature.id,
            status=feature.status,
            reviewed_by=feature.reviewed_by,
            reviewed_at=feature.reviewed_at,
        )
