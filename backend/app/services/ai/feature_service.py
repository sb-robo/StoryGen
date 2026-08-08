from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.feature_extraction.chunk_link import resolve_source_chunk_id
from app.ai.feature_extraction.constraints import format_existing_feature_constraints
from app.ai.feature_extraction.extractor import FeatureExtractor
from app.ai.nodes.feature_extraction import refine_feature_from_answers
from app.ai.openai_client import OpenAIClient
from app.db.models.async_operation import AsyncOperation, OperationStatus, OperationType
from app.db.models.brd_document import BrdStatus
from app.db.models.brd_feature import BrdFeature, FeatureStatus
from app.repositories.brd_chunk_repository import BrdChunkRepository
from app.repositories.brd_repository import BrdRepository
from app.repositories.feature_repository import (
    FeatureRepository,
    decode_clarifying_answers,
    decode_clarifying_questions,
    encode_clarifying_answers,
    encode_clarifying_questions,
    format_clarifying_qa_for_prompt,
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
from app.schemas.pipeline_settings_schema import format_pipeline_context
from app.services.ai._chunk_context import fetch_brd_chunk_context
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
        self.chunk_repo = BrdChunkRepository(db)
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
            source_chunk_id=feature.source_chunk_id,
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

        existing = await self.repo.list_for_brd(operation.user_id, brd.id)
        approved = [
            (f.title, f.description)
            for f in existing
            if f.status == FeatureStatus.APPROVED.value
        ]
        edited_pending = [
            (f.title, f.description)
            for f in existing
            if f.status
            in {FeatureStatus.DRAFT.value, FeatureStatus.PENDING_REVIEW.value}
            and f.updated_at
            and f.created_at
            and f.updated_at > f.created_at
        ]
        existing_constraints = format_existing_feature_constraints(
            approved, edited_pending=edited_pending or None
        )

        extractor = FeatureExtractor(
            self.openai_client,
            self.chunk_repo,
            storage=self.storage,
        )
        output = await extractor.extract(
            brd=brd,
            pipeline_context=format_pipeline_context(
                brd.pipeline_settings, for_stage="features"
            ),
            operation_id=operation_id,
            user_id=operation.user_id,
            existing_constraints=existing_constraints,
        )

        await self.repo.delete_non_finalized_for_brd(brd.id)
        chunks = await self.chunk_repo.list_for_brd(brd.id)

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
                    source_chunk_id=resolve_source_chunk_id(
                        chunks,
                        section_path=item.source_section_path,
                        source_excerpt=item.source_excerpt,
                    ),
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
        questions = decode_clarifying_questions(feature.clarifying_questions)
        answers = decode_clarifying_answers(feature.clarifying_answers)
        unanswered = max(0, len(questions) - len(answers))
        if unanswered > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Answer clarifying questions before approving "
                    f"({unanswered} unanswered)."
                ),
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

    async def reopen_feature(
        self, user_id: int, feature_id: int
    ) -> FeatureReviewResponse:
        feature = await self._get_owned_feature(user_id, feature_id)
        if feature.status != FeatureStatus.REJECTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only rejected features can be reopened.",
            )
        feature.status = FeatureStatus.PENDING_REVIEW.value
        feature.reviewed_by = None
        feature.reviewed_at = None
        feature = await self.repo.update(feature)
        return FeatureReviewResponse(
            id=feature.id,
            status=feature.status,
            reviewed_by=feature.reviewed_by,
            reviewed_at=feature.reviewed_at,
        )

    async def refine_from_answers(self, user_id: int, feature_id: int) -> FeatureResponse:
        """Revise a feature using saved clarifying answers (sync LLM call)."""
        feature = await self._get_owned_feature(user_id, feature_id)
        if feature.status not in {
            FeatureStatus.DRAFT.value,
            FeatureStatus.PENDING_REVIEW.value,
            FeatureStatus.APPROVED.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft, pending_review, or approved features can be refined.",
            )

        questions = decode_clarifying_questions(feature.clarifying_questions)
        answers = decode_clarifying_answers(feature.clarifying_answers)
        if not questions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Feature has no clarifying questions to refine from.",
            )
        if not answers:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Save clarifying answers before refining the feature.",
            )
        if len(answers) < len(questions):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Answer all clarifying questions before refining "
                    f"({len(questions) - len(answers)} unanswered)."
                ),
            )
        if not self.openai_client.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OPENAI_API_KEY is not configured on the server.",
            )

        brd = await self.brd_repo.get_by_id(feature.brd_id)
        if not brd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BRD not found",
            )

        clarifying_qa = format_clarifying_qa_for_prompt(questions, answers)
        brd_context = await fetch_brd_chunk_context(
            self.openai_client,
            self.chunk_repo,
            brd_id=feature.brd_id,
            query_parts=[
                feature.title,
                feature.description,
                feature.source_excerpt,
                clarifying_qa,
            ],
        )
        refined = await refine_feature_from_answers(
            self.openai_client,
            brd_name=brd.name,
            feature_title=feature.title,
            feature_description=feature.description,
            source_excerpt=feature.source_excerpt,
            rationale=feature.rationale,
            confidence=feature.confidence,
            clarifying_qa=clarifying_qa,
            brd_context=brd_context,
            pipeline_context=format_pipeline_context(
                brd.pipeline_settings, for_stage="features"
            ),
            operation_id=None,
            user_id=user_id,
            brd_id=feature.brd_id,
        )

        chunks = await self.chunk_repo.list_for_brd(feature.brd_id)
        feature.title = refined.title.strip()
        feature.description = refined.description.strip()
        feature.confidence = refined.confidence
        feature.rationale = refined.rationale.strip()
        if refined.source_excerpt is not None:
            feature.source_excerpt = refined.source_excerpt
        feature.clarifying_questions = encode_clarifying_questions(
            refined.clarifying_questions
        )
        # Keep existing answers only for questions that remain
        remaining_q = set(refined.clarifying_questions)
        if remaining_q:
            kept = [
                item
                for item in answers
                if item.get("question") in remaining_q and item.get("answer")
            ]
            feature.clarifying_answers = encode_clarifying_answers(kept)
        else:
            feature.clarifying_answers = encode_clarifying_answers([])
        feature.source_chunk_id = resolve_source_chunk_id(
            chunks,
            section_path=refined.source_section_path,
            source_excerpt=feature.source_excerpt,
        ) or feature.source_chunk_id

        if feature.status == FeatureStatus.APPROVED.value:
            feature.status = FeatureStatus.PENDING_REVIEW.value
            feature.reviewed_by = None
            feature.reviewed_at = None

        feature = await self.repo.update(feature)
        return self._to_response(feature)
