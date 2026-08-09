from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.core.dependencies import (
    get_current_user,
    get_feature_service,
    get_operation_service,
    get_sub_feature_service,
)
from app.db.models.user import User
from app.schemas.feature_schema import (
    FeatureResponse,
    FeatureReviewResponse,
    FeatureUpdateRequest,
)
from app.schemas.operation_schema import OperationResponse, OperationResultResponse
from app.schemas.sub_feature_schema import (
    ReviewStatusFilter,
    SubFeatureListResponse,
    SubFeatureReviewResponse,
)
from app.services.ai import FeatureService, SubFeatureService
from app.services.ai.tasks import run_feature_extraction_task
from app.services.operations import OperationService
from app.utils.operation_urls import FEATURE_OPERATION_TYPES

router = APIRouter()


@router.post(
    "/extract/{brd_id}",
    response_model=OperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Extract features from a parsed BRD (async operation)",
    description=(
        "Runs AI feature extraction on parsed Markdown. "
        "Poll `GET /features/status/{operation_id}` then "
        "`GET /features/result/{operation_id}` for the extracted features."
    ),
)
async def extract_brd_features(
    brd_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    feature_service: FeatureService = Depends(get_feature_service),
) -> OperationResponse:
    operation = await feature_service.enqueue_extraction(current_user.id, brd_id)
    background_tasks.add_task(run_feature_extraction_task, operation.operation_id)
    return operation


@router.get(
    "/status/{operation_id}",
    response_model=OperationResponse,
    summary="Get feature pipeline operation status",
    description="Poll for feature_extraction operations until `done` is true.",
)
async def get_feature_operation_status(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    operation_service: OperationService = Depends(get_operation_service),
) -> OperationResponse:
    return await operation_service.get_status(
        current_user.id,
        operation_id,
        allowed_types=FEATURE_OPERATION_TYPES,
    )


@router.get(
    "/result/{operation_id}",
    response_model=OperationResultResponse,
    summary="Get feature pipeline operation result",
    description=(
        "Returns extracted features when the operation succeeded. "
        "Responds 409 while running, 422 if failed."
    ),
)
async def get_feature_operation_result(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    operation_service: OperationService = Depends(get_operation_service),
) -> OperationResultResponse:
    return await operation_service.get_result(
        current_user.id,
        operation_id,
        allowed_types=FEATURE_OPERATION_TYPES,
    )


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
    "/{feature_id}/reopen",
    response_model=FeatureReviewResponse,
    summary="Reopen a rejected feature to pending_review",
)
async def reopen_feature(
    feature_id: int,
    current_user: User = Depends(get_current_user),
    feature_service: FeatureService = Depends(get_feature_service),
) -> FeatureReviewResponse:
    return await feature_service.reopen_feature(current_user.id, feature_id)


@router.post(
    "/{feature_id}/refine-from-answers",
    response_model=FeatureResponse,
    summary="Revise a feature using clarifying answers",
    description=(
        "Runs a sync LLM pass that rewrites the feature from saved clarifying Q&A. "
        "Approved features return to pending_review after refine."
    ),
)
async def refine_feature_from_answers(
    feature_id: int,
    current_user: User = Depends(get_current_user),
    feature_service: FeatureService = Depends(get_feature_service),
) -> FeatureResponse:
    return await feature_service.refine_from_answers(current_user.id, feature_id)


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
