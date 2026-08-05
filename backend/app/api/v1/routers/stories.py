from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.core.dependencies import (
    get_current_user,
    get_operation_service,
    get_story_points_service,
    get_story_service,
    get_test_case_service,
)
from app.db.models.user import User
from app.schemas.operation_schema import OperationResponse, OperationResultResponse
from app.schemas.story_schema import (
    StoryPointsReviewResponse,
    StoryPointsUpdateRequest,
    StoryResponse,
    StoryReviewResponse,
    StoryUpdateRequest,
)
from app.schemas.test_case_schema import TestCaseListResponse, TestCaseStatusFilter
from app.services.ai import StoryPointsService, StoryService, TestCaseService
from app.services.ai.tasks import (
    run_story_point_estimation_task,
    run_test_case_generation_task,
)
from app.services.operations import OperationService
from app.utils.operation_urls import STORY_OPERATION_TYPES

router = APIRouter()


@router.get(
    "/status/{operation_id}",
    response_model=OperationResponse,
    summary="Get story pipeline operation status",
    description=(
        "Poll for story_point_estimation or test_case_generation operations "
        "until `done` is true."
    ),
)
async def get_story_operation_status(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    operation_service: OperationService = Depends(get_operation_service),
) -> OperationResponse:
    return await operation_service.get_status(
        current_user.id,
        operation_id,
        allowed_types=STORY_OPERATION_TYPES,
    )


@router.get(
    "/result/{operation_id}",
    response_model=OperationResultResponse,
    summary="Get story pipeline operation result",
)
async def get_story_operation_result(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    operation_service: OperationService = Depends(get_operation_service),
) -> OperationResultResponse:
    return await operation_service.get_result(
        current_user.id,
        operation_id,
        allowed_types=STORY_OPERATION_TYPES,
    )


@router.patch(
    "/{story_id}",
    response_model=StoryResponse,
    summary="Edit a user story",
)
async def update_story(
    story_id: int,
    payload: StoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    story_service: StoryService = Depends(get_story_service),
) -> StoryResponse:
    return await story_service.update_story(current_user.id, story_id, payload)


@router.post(
    "/{story_id}/approve",
    response_model=StoryReviewResponse,
    summary="Approve a user story after human review",
)
async def approve_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    story_service: StoryService = Depends(get_story_service),
) -> StoryReviewResponse:
    return await story_service.approve_story(current_user.id, story_id)


@router.post(
    "/{story_id}/reject",
    response_model=StoryReviewResponse,
    summary="Reject a user story after human review",
)
async def reject_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    story_service: StoryService = Depends(get_story_service),
) -> StoryReviewResponse:
    return await story_service.reject_story(current_user.id, story_id)


@router.post(
    "/{story_id}/points/estimate",
    response_model=OperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Estimate story points (async, RAG-calibrated when history exists)",
    description=(
        "Poll `GET /stories/status/{operation_id}` then "
        "`GET /stories/result/{operation_id}`."
    ),
)
async def estimate_story_points(
    story_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    story_points_service: StoryPointsService = Depends(get_story_points_service),
) -> OperationResponse:
    operation = await story_points_service.enqueue_estimation(
        current_user.id, story_id
    )
    background_tasks.add_task(run_story_point_estimation_task, operation.operation_id)
    return operation


@router.patch(
    "/{story_id}/points",
    response_model=StoryResponse,
    summary="Override estimated story points before approval",
)
async def override_story_points(
    story_id: int,
    payload: StoryPointsUpdateRequest,
    current_user: User = Depends(get_current_user),
    story_points_service: StoryPointsService = Depends(get_story_points_service),
) -> StoryResponse:
    return await story_points_service.update_points(
        current_user.id, story_id, payload
    )


@router.post(
    "/{story_id}/points/approve",
    response_model=StoryPointsReviewResponse,
    summary="Approve story points and index for future RAG calibration",
)
async def approve_story_points(
    story_id: int,
    current_user: User = Depends(get_current_user),
    story_points_service: StoryPointsService = Depends(get_story_points_service),
) -> StoryPointsReviewResponse:
    return await story_points_service.approve_points(current_user.id, story_id)


@router.post(
    "/{story_id}/test-cases/generate",
    response_model=OperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate test cases for an approved story (async)",
    description=(
        "Poll `GET /stories/status/{operation_id}` then "
        "`GET /stories/result/{operation_id}`."
    ),
)
async def generate_test_cases(
    story_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    test_case_service: TestCaseService = Depends(get_test_case_service),
) -> OperationResponse:
    operation = await test_case_service.enqueue_generation(current_user.id, story_id)
    background_tasks.add_task(run_test_case_generation_task, operation.operation_id)
    return operation


@router.get(
    "/{story_id}/test-cases",
    response_model=TestCaseListResponse,
    summary="List test cases for a story",
)
async def list_test_cases(
    story_id: int,
    status_filter: TestCaseStatusFilter | None = Query(
        default=None,
        alias="status",
        description="Filter by review status",
    ),
    current_user: User = Depends(get_current_user),
    test_case_service: TestCaseService = Depends(get_test_case_service),
) -> TestCaseListResponse:
    return await test_case_service.list_test_cases(
        current_user.id,
        story_id,
        status_filter=status_filter.value if status_filter else None,
    )
