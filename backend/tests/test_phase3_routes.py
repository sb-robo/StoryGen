"""Route-level tests for Phase 3 story points and test case APIs."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.dependencies import get_story_points_service, get_test_case_service
from app.main import app
from app.schemas.operation_schema import OperationResponse
from app.schemas.story_schema import StoryPointsReviewResponse, StoryResponse
from app.schemas.test_case_schema import TestCaseListResponse, TestCaseResponse

NOW = datetime.now(timezone.utc)


class _FakeUser:
    id = 1
    email = "dev@example.com"
    is_active = True
    is_admin = False


def _make_story_response(**overrides) -> StoryResponse:
    fields = dict(
        id=1,
        sub_feature_id=2,
        user_id=1,
        operation_id=None,
        title="Login",
        description="As a user, I want to log in",
        acceptance_criteria=["Valid credentials work"],
        confidence=0.9,
        rationale="Core",
        source_excerpt=None,
        status="approved",
        story_points=5,
        points_rationale="Medium complexity",
        points_status="pending_review",
        points_reviewed_by=None,
        points_reviewed_at=None,
        reviewed_by=1,
        reviewed_at=NOW,
        sort_order=0,
        created_at=NOW,
        updated_at=NOW,
    )
    fields.update(overrides)
    return StoryResponse(**fields)


@pytest.fixture
def mock_story_points_service():
    return MagicMock()


@pytest.fixture
def mock_test_case_service():
    return MagicMock()


@pytest.fixture
def client(mock_story_points_service, mock_test_case_service):
    from app.core.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    app.dependency_overrides[get_story_points_service] = lambda: mock_story_points_service
    app.dependency_overrides[get_test_case_service] = lambda: mock_test_case_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_estimate_points_returns_202(client, mock_story_points_service):
    mock_story_points_service.enqueue_estimation = AsyncMock(
        return_value=OperationResponse(
            operation_id="55555555-5555-5555-5555-555555555555",
            operation_type="story_point_estimation",
            status="pending",
            resource_type="story",
            resource_id=1,
            error_message=None,
            created_at=NOW,
            updated_at=NOW,
            completed_at=None,
        )
    )

    response = client.post("/api/v1/stories/1/points/estimate")

    assert response.status_code == 202
    assert response.json()["operation_type"] == "story_point_estimation"


def test_override_points(client, mock_story_points_service):
    mock_story_points_service.update_points = AsyncMock(
        return_value=_make_story_response(story_points=8)
    )

    response = client.patch(
        "/api/v1/stories/1/points",
        json={"story_points": 8, "points_rationale": "Adjusted for risk"},
    )

    assert response.status_code == 200
    assert response.json()["story_points"] == 8


def test_approve_points(client, mock_story_points_service):
    mock_story_points_service.approve_points = AsyncMock(
        return_value=StoryPointsReviewResponse(
            id=1,
            story_points=5,
            points_status="approved",
            points_reviewed_by=1,
            points_reviewed_at=NOW,
        )
    )

    response = client.post("/api/v1/stories/1/points/approve")

    assert response.status_code == 200
    assert response.json()["points_status"] == "approved"


def test_generate_test_cases_returns_202(client, mock_test_case_service):
    mock_test_case_service.enqueue_generation = AsyncMock(
        return_value=OperationResponse(
            operation_id="66666666-6666-6666-6666-666666666666",
            operation_type="test_case_generation",
            status="pending",
            resource_type="story",
            resource_id=1,
            error_message=None,
            created_at=NOW,
            updated_at=NOW,
            completed_at=None,
        )
    )

    response = client.post("/api/v1/stories/1/test-cases/generate")

    assert response.status_code == 202
    assert response.json()["operation_type"] == "test_case_generation"


def test_generate_test_cases_requires_approved_story(client, mock_test_case_service):
    mock_test_case_service.enqueue_generation = AsyncMock(
        side_effect=HTTPException(status_code=409, detail="Story must be approved")
    )

    response = client.post("/api/v1/stories/1/test-cases/generate")

    assert response.status_code == 409


def test_list_test_cases(client, mock_test_case_service):
    mock_test_case_service.list_test_cases = AsyncMock(
        return_value=TestCaseListResponse.build(
            story_id=1,
            items=[
                TestCaseResponse(
                    id=1,
                    story_id=1,
                    user_id=1,
                    operation_id="op",
                    title="Happy path",
                    steps="1. Login",
                    expected_result="Success",
                    test_type="happy_path",
                    confidence=0.9,
                    rationale="Core",
                    source_excerpt=None,
                    status="pending_review",
                    reviewed_by=None,
                    reviewed_at=None,
                    sort_order=0,
                    created_at=NOW,
                    updated_at=NOW,
                )
            ],
        )
    )

    response = client.get("/api/v1/stories/1/test-cases")

    assert response.status_code == 200
    assert response.json()["total"] == 1
