from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, get_test_case_service
from app.db.models.user import User
from app.schemas.test_case_schema import (
    TestCaseResponse,
    TestCaseReviewResponse,
    TestCaseUpdateRequest,
)
from app.services.ai import TestCaseService

router = APIRouter()


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
