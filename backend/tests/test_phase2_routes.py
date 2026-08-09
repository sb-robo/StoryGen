"""Route-level tests for Phase 2 sub-feature and story APIs."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.dependencies import (
    get_current_user,
    get_story_service,
    get_sub_feature_service,
)
from app.main import app
from app.schemas.operation_schema import OperationResponse
from app.schemas.story_schema import StoryListResponse, StoryResponse, StoryReviewResponse
from app.schemas.sub_feature_schema import (
    SubFeatureListResponse,
    SubFeatureResponse,
    SubFeatureReviewResponse,
)

NOW = datetime.now(timezone.utc)


class _FakeUser:
    id = 1
    email = "dev@example.com"
    is_active = True
    is_admin = False


def _make_operation(**overrides) -> OperationResponse:
    fields = dict(
        operation_id="33333333-3333-3333-3333-333333333333",
        operation_type="sub_feature_generation",
        status="pending",
        resource_type="feature",
        resource_id=5,
        error_message=None,
        created_at=NOW,
        updated_at=NOW,
        completed_at=None,
    )
    fields.update(overrides)
    return OperationResponse(**fields)


def _make_sub_feature(**overrides) -> SubFeatureResponse:
    fields = dict(
        id=1,
        feature_id=5,
        user_id=1,
        operation_id="33333333-3333-3333-3333-333333333333",
        title="OAuth login",
        description="Social login flow",
        confidence=0.85,
        rationale="Distinct from password login",
        source_excerpt=None,
        status="pending_review",
        reviewed_by=None,
        reviewed_at=None,
        sort_order=0,
        created_at=NOW,
        updated_at=NOW,
    )
    fields.update(overrides)
    return SubFeatureResponse(**fields)


def _make_story(**overrides) -> StoryResponse:
    fields = dict(
        id=1,
        sub_feature_id=2,
        user_id=1,
        operation_id="44444444-4444-4444-4444-444444444444",
        title="Login with Google",
        description="As a user, I want to log in with Google, so that signup is faster",
        acceptance_criteria=["OAuth redirect works"],
        confidence=0.9,
        rationale="Primary OAuth path",
        source_excerpt=None,
        status="pending_review",
        story_points=None,
        points_rationale=None,
        reviewed_by=None,
        reviewed_at=None,
        sort_order=0,
        created_at=NOW,
        updated_at=NOW,
    )
    fields.update(overrides)
    return StoryResponse(**fields)


@pytest.fixture
def mock_sub_feature_service():
    return MagicMock()


@pytest.fixture
def mock_story_service():
    return MagicMock()


@pytest.fixture
def client(mock_sub_feature_service, mock_story_service):
    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    app.dependency_overrides[get_sub_feature_service] = lambda: mock_sub_feature_service
    app.dependency_overrides[get_story_service] = lambda: mock_story_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_generate_sub_features_returns_202(client, mock_sub_feature_service):
    mock_sub_feature_service.enqueue_generation = AsyncMock(
        return_value=_make_operation()
    )

    response = client.post("/api/v1/sub-features/generate/5")

    assert response.status_code == 202
    assert response.json()["operation_type"] == "sub_feature_generation"


def test_generate_sub_features_requires_approved_feature(client, mock_sub_feature_service):
    mock_sub_feature_service.enqueue_generation = AsyncMock(
        side_effect=HTTPException(status_code=409, detail="Feature must be approved")
    )

    response = client.post("/api/v1/sub-features/generate/5")

    assert response.status_code == 409


def test_list_sub_features(client, mock_sub_feature_service):
    mock_sub_feature_service.list_sub_features = AsyncMock(
        return_value=SubFeatureListResponse.build(
            feature_id=5,
            items=[_make_sub_feature()],
        )
    )

    response = client.get("/api/v1/features/5/sub-features")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_approve_sub_feature(client, mock_sub_feature_service):
    mock_sub_feature_service.approve_sub_feature = AsyncMock(
        return_value=SubFeatureReviewResponse(
            id=1, status="approved", reviewed_by=1, reviewed_at=NOW
        )
    )

    response = client.post("/api/v1/sub-features/1/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_generate_stories_returns_202(client, mock_story_service):
    mock_story_service.enqueue_generation = AsyncMock(
        return_value=_make_operation(
            operation_id="44444444-4444-4444-4444-444444444444",
            operation_type="story_generation",
            resource_type="sub_feature",
            resource_id=2,
        )
    )

    response = client.post("/api/v1/stories/generate/2")

    assert response.status_code == 202
    assert response.json()["operation_type"] == "story_generation"


def test_list_stories(client, mock_story_service):
    mock_story_service.list_stories = AsyncMock(
        return_value=StoryListResponse.build(
            sub_feature_id=2,
            items=[_make_story()],
        )
    )

    response = client.get("/api/v1/sub-features/2/stories")

    assert response.status_code == 200
    assert response.json()["items"][0]["title"] == "Login with Google"


def test_approve_story(client, mock_story_service):
    mock_story_service.approve_story = AsyncMock(
        return_value=StoryReviewResponse(
            id=1, status="approved", reviewed_by=1, reviewed_at=NOW
        )
    )

    response = client.post("/api/v1/stories/1/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
