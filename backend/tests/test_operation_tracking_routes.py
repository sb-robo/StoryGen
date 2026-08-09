"""Tests for per-resource operation status/result endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_operation_service
from app.main import app
from app.schemas.operation_schema import OperationResponse

NOW = datetime.now(timezone.utc)


class _FakeUser:
    id = 1
    email = "dev@example.com"
    is_active = True
    is_admin = False


@pytest.fixture
def mock_operation_service():
    return MagicMock()


@pytest.fixture
def client(mock_operation_service):
    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    app.dependency_overrides[get_operation_service] = lambda: mock_operation_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_feature_status_endpoint(client, mock_operation_service):
    mock_operation_service.get_status = AsyncMock(
        return_value=OperationResponse(
            operation_id="22222222-2222-2222-2222-222222222222",
            operation_type="feature_extraction",
            status="running",
            resource_type="brd",
            resource_id=10,
            error_message=None,
            created_at=NOW,
            updated_at=NOW,
            completed_at=None,
        )
    )

    response = client.get(
        "/api/v1/features/status/22222222-2222-2222-2222-222222222222"
    )

    assert response.status_code == 200
    mock_operation_service.get_status.assert_awaited_once()
    kwargs = mock_operation_service.get_status.await_args.kwargs
    assert kwargs["allowed_types"] == {"feature_extraction"}


def test_brd_status_rejects_feature_operation(client, mock_operation_service):
    mock_operation_service.get_status = AsyncMock(
        side_effect=HTTPException(status_code=404, detail="Operation not found")
    )

    response = client.get(
        "/api/v1/brds/status/22222222-2222-2222-2222-222222222222"
    )

    assert response.status_code == 404
    kwargs = mock_operation_service.get_status.await_args.kwargs
    assert kwargs["allowed_types"] == {"brd_upload", "brd_reparse"}


def test_story_status_endpoint(client, mock_operation_service):
    mock_operation_service.get_status = AsyncMock(
        return_value=OperationResponse(
            operation_id="44444444-4444-4444-4444-444444444444",
            operation_type="story_point_estimation",
            status="succeeded",
            resource_type="story",
            resource_id=1,
            error_message=None,
            created_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
        )
    )

    response = client.get(
        "/api/v1/stories/status/44444444-4444-4444-4444-444444444444"
    )

    assert response.status_code == 200
    assert response.json()["done"] is True
    kwargs = mock_operation_service.get_status.await_args.kwargs
    assert kwargs["allowed_types"] == {
        "story_generation",
        "story_point_estimation",
    }


def test_sub_feature_status_endpoint(client, mock_operation_service):
    mock_operation_service.get_status = AsyncMock(
        return_value=OperationResponse(
            operation_id="55555555-5555-5555-5555-555555555555",
            operation_type="sub_feature_generation",
            status="succeeded",
            resource_type="feature",
            resource_id=1,
            error_message=None,
            created_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
        )
    )

    response = client.get(
        "/api/v1/sub-features/status/55555555-5555-5555-5555-555555555555"
    )

    assert response.status_code == 200
    kwargs = mock_operation_service.get_status.await_args.kwargs
    assert kwargs["allowed_types"] == {"sub_feature_generation"}


def test_test_case_status_endpoint(client, mock_operation_service):
    mock_operation_service.get_status = AsyncMock(
        return_value=OperationResponse(
            operation_id="66666666-6666-6666-6666-666666666666",
            operation_type="test_case_generation",
            status="succeeded",
            resource_type="story",
            resource_id=1,
            error_message=None,
            created_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
        )
    )

    response = client.get(
        "/api/v1/test-cases/status/66666666-6666-6666-6666-666666666666"
    )

    assert response.status_code == 200
    kwargs = mock_operation_service.get_status.await_args.kwargs
    assert kwargs["allowed_types"] == {"test_case_generation"}
