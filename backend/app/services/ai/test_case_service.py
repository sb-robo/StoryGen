from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.test_case_generation import generate_test_cases_for_story
from app.ai.feature_extraction.chunk_link import resolve_source_chunk_id
from app.ai.openai_client import OpenAIClient
from app.db.models.async_operation import AsyncOperation, OperationStatus, OperationType
from app.db.models.brd_story import BrdStory, StoryReviewStatus
from app.db.models.brd_test_case import BrdTestCase, TestCaseStatus
from app.repositories.brd_chunk_repository import BrdChunkRepository
from app.repositories.brd_repository import BrdRepository
from app.repositories.feature_repository import FeatureRepository
from app.repositories.operation_repository import OperationRepository
from app.repositories.story_repository import StoryRepository, decode_acceptance_criteria
from app.repositories.sub_feature_repository import SubFeatureRepository
from app.repositories.test_case_repository import TestCaseRepository
from app.schemas.operation_schema import OperationResponse
from app.schemas.pipeline_settings_schema import format_pipeline_context
from app.schemas.test_case_schema import (
    TestCaseGenerationResultResponse,
    TestCaseListResponse,
    TestCaseResponse,
    TestCaseReviewResponse,
    TestCaseUpdateRequest,
)
from app.services.ai._chunk_context import fetch_brd_chunk_context
from app.services.ai._helpers import ensure_operation_not_running, operation_response


class TestCaseService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        openai_client: OpenAIClient | None = None,
    ):
        self.db = db
        self.repo = TestCaseRepository(db)
        self.story_repo = StoryRepository(db)
        self.sub_feature_repo = SubFeatureRepository(db)
        self.feature_repo = FeatureRepository(db)
        self.brd_repo = BrdRepository(db)
        self.chunk_repo = BrdChunkRepository(db)
        self.operation_repo = OperationRepository(db)
        self.openai_client = openai_client or OpenAIClient(db)

    def _to_response(self, item: BrdTestCase) -> TestCaseResponse:
        return TestCaseResponse(
            id=item.id,
            story_id=item.story_id,
            user_id=item.user_id,
            operation_id=item.operation_id,
            title=item.title,
            steps=item.steps,
            expected_result=item.expected_result,
            test_type=item.test_type,
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

    async def enqueue_generation(self, user_id: int, story_id: int) -> OperationResponse:
        story = await self._get_owned_story(user_id, story_id)
        if story.status != StoryReviewStatus.APPROVED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Story must be approved before generating test cases.",
            )
        if not self.openai_client.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OPENAI_API_KEY is not configured on the server.",
            )

        await ensure_operation_not_running(
            self.operation_repo,
            user_id=user_id,
            operation_type=OperationType.TEST_CASE_GENERATION.value,
            resource_type="story",
            resource_id=story_id,
            conflict_message="Test case generation is already running for this story.",
        )

        operation = await self.operation_repo.create(
            AsyncOperation(
                user_id=user_id,
                operation_type=OperationType.TEST_CASE_GENERATION.value,
                status=OperationStatus.PENDING.value,
                resource_type="story",
                resource_id=story_id,
            )
        )
        await self.db.commit()
        return operation_response(operation)

    async def complete_generation(self, operation_id: str) -> list[BrdTestCase] | None:
        operation = await self.operation_repo.get_by_id(operation_id)
        if not operation or operation.resource_id is None:
            return None

        story = await self.story_repo.get_by_id(operation.resource_id)
        if not story:
            return None

        brd_id = await self._brd_id_for_story(story)
        ac = decode_acceptance_criteria(story.acceptance_criteria)
        brd = await self.brd_repo.get_by_id(brd_id)
        brd_context = await fetch_brd_chunk_context(
            self.openai_client,
            self.chunk_repo,
            brd_id=brd_id,
            query_parts=[
                story.title,
                story.description,
                "\n".join(ac),
                story.source_excerpt,
            ],
        )

        output = await generate_test_cases_for_story(
            self.openai_client,
            title=story.title,
            description=story.description,
            acceptance_criteria=ac,
            brd_context=brd_context,
            pipeline_context=format_pipeline_context(
                brd.pipeline_settings if brd else None, for_stage="tests"
            ),
            operation_id=operation_id,
            user_id=operation.user_id,
            brd_id=brd_id,
        )

        await self.repo.delete_non_finalized_for_story(story.id)
        chunks = await self.chunk_repo.list_for_brd(brd_id)

        items: list[BrdTestCase] = []
        for idx, item in enumerate(output.test_cases):
            items.append(
                BrdTestCase(
                    story_id=story.id,
                    user_id=operation.user_id,
                    operation_id=operation_id,
                    title=item.title.strip(),
                    steps=item.steps.strip(),
                    expected_result=item.expected_result.strip(),
                    test_type=item.test_type,
                    confidence=item.confidence,
                    rationale=item.rationale.strip(),
                    source_excerpt=item.source_excerpt,
                    source_chunk_id=resolve_source_chunk_id(
                        chunks,
                        section_path=item.source_section_path,
                        source_excerpt=item.source_excerpt,
                    ),
                    status=TestCaseStatus.PENDING_REVIEW.value,
                    sort_order=idx,
                )
            )

        if not items:
            raise RuntimeError("Test case generation returned no items")

        return await self.repo.create_many(items)

    async def list_test_cases(
        self,
        user_id: int,
        story_id: int,
        *,
        status_filter: str | None = None,
    ) -> TestCaseListResponse:
        await self._get_owned_story(user_id, story_id)
        items = await self.repo.list_for_story(user_id, story_id, status=status_filter)
        return TestCaseListResponse.build(
            story_id=story_id,
            items=[self._to_response(item) for item in items],
        )

    async def get_generation_result(
        self, user_id: int, operation_id: str
    ) -> TestCaseGenerationResultResponse:
        operation = await self.operation_repo.get_by_id_for_user(operation_id, user_id)
        if not operation or operation.resource_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation not found",
            )
        if operation.operation_type != OperationType.TEST_CASE_GENERATION.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation is not a test case generation",
            )

        items = await self.repo.list_for_story(user_id, operation.resource_id)
        matched = [i for i in items if i.operation_id == operation_id]
        return TestCaseGenerationResultResponse.build(
            story_id=operation.resource_id,
            operation_id=operation_id,
            test_cases=[self._to_response(item) for item in matched],
        )

    async def update_test_case(
        self, user_id: int, test_case_id: int, payload: TestCaseUpdateRequest
    ) -> TestCaseResponse:
        item = await self.repo.get_by_id_for_user(test_case_id, user_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test case not found",
            )
        if item.status not in {
            TestCaseStatus.DRAFT.value,
            TestCaseStatus.PENDING_REVIEW.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft or pending_review test cases can be edited.",
            )

        if payload.title is not None:
            item.title = payload.title.strip()
        if payload.steps is not None:
            item.steps = payload.steps.strip()
        if payload.expected_result is not None:
            item.expected_result = payload.expected_result.strip()
        if payload.test_type is not None:
            item.test_type = payload.test_type

        item = await self.repo.update(item)
        return self._to_response(item)

    async def approve_test_case(
        self, user_id: int, test_case_id: int
    ) -> TestCaseReviewResponse:
        item = await self.repo.get_by_id_for_user(test_case_id, user_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test case not found",
            )
        if item.status != TestCaseStatus.PENDING_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending_review test cases can be approved.",
            )
        item.status = TestCaseStatus.APPROVED.value
        item.reviewed_by = user_id
        item.reviewed_at = datetime.now(timezone.utc)
        item = await self.repo.update(item)
        return TestCaseReviewResponse(
            id=item.id,
            status=item.status,
            reviewed_by=item.reviewed_by,
            reviewed_at=item.reviewed_at,
        )

    async def reject_test_case(
        self, user_id: int, test_case_id: int
    ) -> TestCaseReviewResponse:
        item = await self.repo.get_by_id_for_user(test_case_id, user_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test case not found",
            )
        if item.status != TestCaseStatus.PENDING_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending_review test cases can be rejected.",
            )
        item.status = TestCaseStatus.REJECTED.value
        item.reviewed_by = user_id
        item.reviewed_at = datetime.now(timezone.utc)
        item = await self.repo.update(item)
        return TestCaseReviewResponse(
            id=item.id,
            status=item.status,
            reviewed_by=item.reviewed_by,
            reviewed_at=item.reviewed_at,
        )

    async def reopen_test_case(
        self, user_id: int, test_case_id: int
    ) -> TestCaseReviewResponse:
        item = await self.repo.get_by_id_for_user(test_case_id, user_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test case not found",
            )
        if item.status != TestCaseStatus.REJECTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only rejected test cases can be reopened.",
            )
        item.status = TestCaseStatus.PENDING_REVIEW.value
        item.reviewed_by = None
        item.reviewed_at = None
        item = await self.repo.update(item)
        return TestCaseReviewResponse(
            id=item.id,
            status=item.status,
            reviewed_by=item.reviewed_by,
            reviewed_at=item.reviewed_at,
        )
