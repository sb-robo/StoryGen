"""Route tests for admin operations list and SSE stream auth."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_admin, get_current_user, get_operation_service
from app.main import app
from app.schemas.operation_schema import OperationListResponse, OperationResponse

NOW = datetime.now(timezone.utc)


class _AdminUser:
    id = 1
    email = "admin@example.com"
    is_active = True
    is_admin = True


class _NormalUser:
    id = 2
    email = "user@example.com"
    is_active = True
    is_admin = False


def _op(**overrides) -> OperationResponse:
    fields = dict(
        operation_id="11111111-1111-1111-1111-111111111111",
        operation_type="feature_extraction",
        status="running",
        user_id=2,
        resource_type="brd",
        resource_id=1,
        error_message=None,
        created_at=NOW,
        updated_at=NOW,
        completed_at=None,
    )
    fields.update(overrides)
    return OperationResponse(**fields)


@pytest.fixture
def mock_operation_service():
    return MagicMock()


@pytest.fixture
def admin_client(mock_operation_service):
    app.dependency_overrides[get_current_user] = lambda: _AdminUser()
    app.dependency_overrides[get_current_admin] = lambda: _AdminUser()
    app.dependency_overrides[get_operation_service] = lambda: mock_operation_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def user_client(mock_operation_service):
    def _forbid_admin():
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Admin access required")

    app.dependency_overrides[get_current_user] = lambda: _NormalUser()
    app.dependency_overrides[get_current_admin] = _forbid_admin
    app.dependency_overrides[get_operation_service] = lambda: mock_operation_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_list_operations_requires_admin(user_client):
    response = user_client.get("/api/v1/operations")
    assert response.status_code == 403


def test_list_operations_admin_ok(admin_client, mock_operation_service):
    mock_operation_service.list_operations_admin = AsyncMock(
        return_value=OperationListResponse.build(
            items=[_op()],
            total=1,
            page=1,
            page_size=20,
            status=None,
            operation_type=None,
            resource_type=None,
            resource_id=None,
            sort_by="created_at",
            sort_order="desc",
            user_id=None,
        )
    )

    response = admin_client.get("/api/v1/operations")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["user_id"] == 2
    mock_operation_service.list_operations_admin.assert_awaited()


def test_list_operations_admin_filters_by_user(admin_client, mock_operation_service):
    mock_operation_service.list_operations_admin = AsyncMock(
        return_value=OperationListResponse.build(
            items=[],
            total=0,
            page=1,
            page_size=20,
            status=None,
            operation_type=None,
            resource_type=None,
            resource_id=None,
            sort_by="created_at",
            sort_order="desc",
            user_id=9,
        )
    )

    response = admin_client.get("/api/v1/operations?user_id=9")

    assert response.status_code == 200
    kwargs = mock_operation_service.list_operations_admin.await_args.kwargs
    assert kwargs["user_id"] == 9
