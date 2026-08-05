from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.core.dependencies import get_current_user, get_feature_service, get_sub_feature_service
from app.db.models.user import User
from app.schemas.feature_schema import (
    FeatureResponse,
    FeatureReviewResponse,
    FeatureUpdateRequest,
)
from app.schemas.operation_schema import OperationResponse
from app.schemas.sub_feature_schema import (
    ReviewStatusFilter,
    SubFeatureListResponse,
    SubFeatureReviewResponse,
)
from app.services.ai import FeatureService, SubFeatureService
from app.services.ai.tasks import run_sub_feature_generation_task

router = APIRouter()


@router.patch(
    "/{feature_id}",
    response_model=FeatureResponse,
    summary="Edit a feature or answer clarifying questions",
)
async def update_feature(
    feature_id: int,
    payload: FeatureUpdateRequest,
    current_user: User = Depends(get_current_user),
    feature_service: FeatureService = Depends(get_feature_service),
) -> FeatureResponse:
    return await feature_service.update_feature(current_user.id, feature_id, payload)


@router.post(
    "/{feature_id}/approve",
    response_model=FeatureReviewResponse,
    summary="Approve a feature after human review",
)
async def approve_feature(
    feature_id: int,
    current_user: User = Depends(get_current_user),
    feature_service: FeatureService = Depends(get_feature_service),
) -> FeatureReviewResponse:
    return await feature_service.approve_feature(current_user.id, feature_id)


@router.post(
    "/{feature_id}/reject",
    response_model=FeatureReviewResponse,
    summary="Reject a feature after human review",
)
async def reject_feature(
    feature_id: int,
    current_user: User = Depends(get_current_user),
    feature_service: FeatureService = Depends(get_feature_service),
) -> FeatureReviewResponse:
    return await feature_service.reject_feature(current_user.id, feature_id)


@router.post(
    "/{feature_id}/sub-features/generate",
    response_model=OperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate sub-features from an approved feature (async)",
)
async def generate_sub_features(
    feature_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    sub_feature_service: SubFeatureService = Depends(get_sub_feature_service),
) -> OperationResponse:
    operation = await sub_feature_service.enqueue_generation(
        current_user.id, feature_id
    )
    background_tasks.add_task(run_sub_feature_generation_task, operation.operation_id)
    return operation


@router.get(
    "/{feature_id}/sub-features",
    response_model=SubFeatureListResponse,
    summary="List sub-features for a feature",
)
async def list_sub_features(
    feature_id: int,
    status_filter: ReviewStatusFilter | None = Query(
        default=None,
        alias="status",
        description="Filter by review status",
    ),
    current_user: User = Depends(get_current_user),
    sub_feature_service: SubFeatureService = Depends(get_sub_feature_service),
) -> SubFeatureListResponse:
    return await sub_feature_service.list_sub_features(
        current_user.id,
        feature_id,
        status_filter=status_filter.value if status_filter else None,
    )
