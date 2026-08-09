"""
Route-level tests for feature extraction and review APIs.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_feature_service
from app.main import app
from app.schemas.feature_schema import FeatureListResponse, FeatureResponse, FeatureReviewResponse
from app.schemas.operation_schema import OperationResponse

NOW = datetime.now(timezone.utc)


class _FakeUser:
    id = 1
    email = "dev@example.com"
    is_active = True
    is_admin = False


def _make_feature_response(**overrides) -> FeatureResponse:
    fields = dict(
        id=1,
        brd_id=10,
        user_id=1,
        operation_id="22222222-2222-2222-2222-222222222222",
        title="User Login",
        description="Authenticate users",
        confidence=0.9,
        rationale="Section 2",
        clarifying_questions=[],
        clarifying_answers=[],
        source_excerpt="Users must log in",
        status="pending_review",
        reviewed_by=None,
        reviewed_at=None,
        sort_order=0,
        created_at=NOW,
        updated_at=NOW,
    )
    fields.update(overrides)
    return FeatureResponse(**fields)


def _make_operation_response(**overrides) -> OperationResponse:
    fields = dict(
        operation_id="22222222-2222-2222-2222-222222222222",
        operation_type="feature_extraction",
        status="pending",
        resource_type="brd",
        resource_id=10,
        error_message=None,
        created_at=NOW,
        updated_at=NOW,
        completed_at=None,
    )
    fields.update(overrides)
    return OperationResponse(**fields)


@pytest.fixture
def mock_feature_service():
    return MagicMock()


@pytest.fixture
def client(mock_feature_service):
    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    app.dependency_overrides[get_feature_service] = lambda: mock_feature_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_extract_features_returns_202(client, mock_feature_service):
    mock_feature_service.enqueue_extraction = AsyncMock(
        return_value=_make_operation_response()
    )

    response = client.post("/api/v1/features/extract/10")

    assert response.status_code == 202
    body = response.json()
    assert body["operation_type"] == "feature_extraction"
    assert body["resource_id"] == 10


def test_extract_features_propagates_unparsed_brd_conflict(client, mock_feature_service):
    mock_feature_service.enqueue_extraction = AsyncMock(
        side_effect=HTTPException(status_code=409, detail="BRD must be parsed")
    )

    response = client.post("/api/v1/features/extract/10")

    assert response.status_code == 409


def test_list_features(client, mock_feature_service):
    mock_feature_service.list_features = AsyncMock(
        return_value=FeatureListResponse.build(
            brd_id=10,
            items=[_make_feature_response()],
        )
    )

    response = client.get("/api/v1/brds/10/features")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "User Login"


def test_approve_feature(client, mock_feature_service):
    mock_feature_service.approve_feature = AsyncMock(
        return_value=FeatureReviewResponse(
            id=1,
            status="approved",
            reviewed_by=1,
            reviewed_at=NOW,
        )
    )

    response = client.post("/api/v1/features/1/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_reject_feature(client, mock_feature_service):
    mock_feature_service.reject_feature = AsyncMock(
        return_value=FeatureReviewResponse(
            id=1,
            status="rejected",
            reviewed_by=1,
            reviewed_at=NOW,
        )
    )

    response = client.post("/api/v1/features/1/reject")

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_reopen_feature(client, mock_feature_service):
    mock_feature_service.reopen_feature = AsyncMock(
        return_value=FeatureReviewResponse(
            id=1,
            status="pending_review",
            reviewed_by=None,
            reviewed_at=None,
        )
    )

    response = client.post("/api/v1/features/1/reopen")

    assert response.status_code == 200
    assert response.json()["status"] == "pending_review"


def test_approve_feature_propagates_clarifying_conflict(client, mock_feature_service):
    mock_feature_service.approve_feature = AsyncMock(
        side_effect=HTTPException(
            status_code=409,
            detail="Answer clarifying questions before approving (2 unanswered).",
        )
    )

    response = client.post("/api/v1/features/1/approve")

    assert response.status_code == 409
    assert "clarifying" in response.json()["detail"].lower()


def test_update_feature(client, mock_feature_service):
    mock_feature_service.update_feature = AsyncMock(
        return_value=_make_feature_response(title="Updated Login")
    )

    response = client.patch(
        "/api/v1/features/1",
        json={"title": "Updated Login"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Login"
