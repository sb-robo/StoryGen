from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.core.dependencies import (
    get_current_user,
    get_operation_service,
    get_test_case_service,
)
from app.db.models.user import User
from app.schemas.operation_schema import OperationResponse, OperationResultResponse
from app.schemas.test_case_schema import (
    TestCaseResponse,
    TestCaseReviewResponse,
    TestCaseUpdateRequest,
)
from app.services.ai import TestCaseService
from app.services.ai.tasks import run_test_case_generation_task
from app.services.operations import OperationService
from app.utils.operation_urls import TEST_CASE_OPERATION_TYPES

router = APIRouter()


@router.post(
    "/generate/{story_id}",
    response_model=OperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate test cases for an approved story (async)",
    description=(
        "Poll `GET /test-cases/status/{operation_id}` then "
        "`GET /test-cases/result/{operation_id}`."
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
    "/status/{operation_id}",
    response_model=OperationResponse,
    summary="Get test case generation operation status",
    description="Poll for test_case_generation operations until `done` is true.",
)
async def get_test_case_operation_status(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    operation_service: OperationService = Depends(get_operation_service),
) -> OperationResponse:
    return await operation_service.get_status(
        current_user.id,
        operation_id,
        allowed_types=TEST_CASE_OPERATION_TYPES,
    )


@router.get(
    "/result/{operation_id}",
    response_model=OperationResultResponse,
    summary="Get test case generation operation result",
)
async def get_test_case_operation_result(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    operation_service: OperationService = Depends(get_operation_service),
) -> OperationResultResponse:
    return await operation_service.get_result(
        current_user.id,
        operation_id,
        allowed_types=TEST_CASE_OPERATION_TYPES,
    )


@router.patch(
    "/{test_case_id}",
    response_model=TestCaseResponse,
    summary="Edit a test case",
)
async def update_test_case(
    test_case_id: int,
    payload: TestCaseUpdateRequest,
    current_user: User = Depends(get_current_user),
    test_case_service: TestCaseService = Depends(get_test_case_service),
) -> TestCaseResponse:
    return await test_case_service.update_test_case(
        current_user.id, test_case_id, payload
    )


@router.post(
    "/{test_case_id}/approve",
    response_model=TestCaseReviewResponse,
    summary="Approve a test case after human review",
)
async def approve_test_case(
    test_case_id: int,
    current_user: User = Depends(get_current_user),
    test_case_service: TestCaseService = Depends(get_test_case_service),
) -> TestCaseReviewResponse:
    return await test_case_service.approve_test_case(current_user.id, test_case_id)


@router.post(
    "/{test_case_id}/reject",
    response_model=TestCaseReviewResponse,
    summary="Reject a test case after human review",
)
async def reject_test_case(
    test_case_id: int,
    current_user: User = Depends(get_current_user),
    test_case_service: TestCaseService = Depends(get_test_case_service),
) -> TestCaseReviewResponse:
    return await test_case_service.reject_test_case(current_user.id, test_case_id)


@router.post(
    "/{test_case_id}/reopen",
    response_model=TestCaseReviewResponse,
    summary="Reopen a rejected test case to pending_review",
)
async def reopen_test_case(
    test_case_id: int,
    current_user: User = Depends(get_current_user),
    test_case_service: TestCaseService = Depends(get_test_case_service),
) -> TestCaseReviewResponse:
    return await test_case_service.reopen_test_case(current_user.id, test_case_id)
