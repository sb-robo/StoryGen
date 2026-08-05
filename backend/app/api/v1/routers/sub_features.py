from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.core.dependencies import (
    get_current_user,
    get_operation_service,
    get_story_service,
    get_sub_feature_service,
)
from app.db.models.user import User
from app.schemas.operation_schema import OperationResponse, OperationResultResponse
from app.schemas.story_schema import StoryListResponse, StoryStatusFilter
from app.schemas.sub_feature_schema import (
    SubFeatureResponse,
    SubFeatureReviewResponse,
    SubFeatureUpdateRequest,
)
from app.services.ai import StoryService, SubFeatureService
from app.services.ai.tasks import run_story_generation_task
from app.services.operations import OperationService
from app.utils.operation_urls import SUB_FEATURE_OPERATION_TYPES

router = APIRouter()


@router.get(
    "/status/{operation_id}",
    response_model=OperationResponse,
    summary="Get sub-feature story generation operation status",
)
async def get_sub_feature_operation_status(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    operation_service: OperationService = Depends(get_operation_service),
) -> OperationResponse:
    return await operation_service.get_status(
        current_user.id,
        operation_id,
        allowed_types=SUB_FEATURE_OPERATION_TYPES,
    )


@router.get(
    "/result/{operation_id}",
    response_model=OperationResultResponse,
    summary="Get sub-feature story generation operation result",
)
async def get_sub_feature_operation_result(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    operation_service: OperationService = Depends(get_operation_service),
) -> OperationResultResponse:
    return await operation_service.get_result(
        current_user.id,
        operation_id,
        allowed_types=SUB_FEATURE_OPERATION_TYPES,
    )


@router.patch(
    "/{sub_feature_id}",
    response_model=SubFeatureResponse,
    summary="Edit a sub-feature",
)
async def update_sub_feature(
    sub_feature_id: int,
    payload: SubFeatureUpdateRequest,
    current_user: User = Depends(get_current_user),
    sub_feature_service: SubFeatureService = Depends(get_sub_feature_service),
) -> SubFeatureResponse:
    return await sub_feature_service.update_sub_feature(
        current_user.id, sub_feature_id, payload
    )


@router.post(
    "/{sub_feature_id}/approve",
    response_model=SubFeatureReviewResponse,
    summary="Approve a sub-feature after human review",
)
async def approve_sub_feature(
    sub_feature_id: int,
    current_user: User = Depends(get_current_user),
    sub_feature_service: SubFeatureService = Depends(get_sub_feature_service),
) -> SubFeatureReviewResponse:
    return await sub_feature_service.approve_sub_feature(
        current_user.id, sub_feature_id
    )


@router.post(
    "/{sub_feature_id}/reject",
    response_model=SubFeatureReviewResponse,
    summary="Reject a sub-feature after human review",
)
async def reject_sub_feature(
    sub_feature_id: int,
    current_user: User = Depends(get_current_user),
    sub_feature_service: SubFeatureService = Depends(get_sub_feature_service),
) -> SubFeatureReviewResponse:
    return await sub_feature_service.reject_sub_feature(
        current_user.id, sub_feature_id
    )


@router.post(
    "/{sub_feature_id}/stories/generate",
    response_model=OperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate user stories from an approved sub-feature (async)",
    description=(
        "Poll `GET /sub-features/status/{operation_id}` then "
        "`GET /sub-features/result/{operation_id}`."
    ),
)
async def generate_stories(
    sub_feature_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    story_service: StoryService = Depends(get_story_service),
) -> OperationResponse:
    operation = await story_service.enqueue_generation(
        current_user.id, sub_feature_id
    )
    background_tasks.add_task(run_story_generation_task, operation.operation_id)
    return operation


@router.get(
    "/{sub_feature_id}/stories",
    response_model=StoryListResponse,
    summary="List stories for a sub-feature",
)
async def list_stories(
    sub_feature_id: int,
    status_filter: StoryStatusFilter | None = Query(
        default=None,
        alias="status",
        description="Filter by review status",
    ),
    current_user: User = Depends(get_current_user),
    story_service: StoryService = Depends(get_story_service),
) -> StoryListResponse:
    return await story_service.list_stories(
        current_user.id,
        sub_feature_id,
        status_filter=status_filter.value if status_filter else None,
    )
