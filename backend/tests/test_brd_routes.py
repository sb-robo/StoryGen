"""
Route-level tests for the BRD API.

These exercise the actual FastAPI routing/validation/response-model layer via
TestClient, with `get_brd_service` / `get_operation_service` / `get_current_user`
overridden so no real database or filesystem is touched.
"""

from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_brd_service, get_current_user, get_operation_service
from app.main import app
from app.schemas.brd_schema import BrdDetailResponse, BrdListResponse, BrdResponse
from app.schemas.operation_schema import OperationResponse

NOW = datetime.now(timezone.utc)


class _FakeUser:
    id = 1
    email = "dev@example.com"
    is_active = True
    is_admin = False


def _make_brd_response(**overrides) -> BrdResponse:
    fields = dict(
        id=1,
        user_id=1,
        name="Payments BRD",
        original_filename="spec.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size_bytes=1024,
        status="parsed",
        error_message=None,
        page_count=3,
        table_count=1,
        image_count=2,
        created_at=NOW,
        updated_at=NOW,
        preview="Some preview text",
    )
    fields.update(overrides)
    return BrdResponse(**fields)


def _make_operation_response(**overrides) -> OperationResponse:
    fields = dict(
        operation_id="11111111-1111-1111-1111-111111111111",
        operation_type="brd_upload",
        status="running",
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
def mock_brd_service():
    return MagicMock()


@pytest.fixture
def mock_operation_service():
    return MagicMock()


@pytest.fixture
def client(mock_brd_service, mock_operation_service):
    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    app.dependency_overrides[get_brd_service] = lambda: mock_brd_service
    app.dependency_overrides[get_operation_service] = lambda: mock_operation_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_upload_brd_returns_202_with_operation_id(client, mock_brd_service):
    mock_brd_service.upload = AsyncMock(return_value=_make_operation_response())

    response = client.post(
        "/api/v1/brds/upload",
        data={"name": "Payments BRD"},
        files={"file": ("spec.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["operation_id"] == "11111111-1111-1111-1111-111111111111"
    assert body["status_url"] == "/api/v1/brds/status/11111111-1111-1111-1111-111111111111"
    assert body["done"] is False


def test_upload_brd_propagates_duplicate_name_conflict(client, mock_brd_service):
    from fastapi import HTTPException

    mock_brd_service.upload = AsyncMock(
        side_effect=HTTPException(status_code=409, detail="A BRD named 'x' already exists.")
    )

    response = client.post(
        "/api/v1/brds/upload",
        data={"name": "Payments BRD"},
        files={"file": ("spec.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )

    assert response.status_code == 409


def test_list_brds_returns_paginated_payload(client, mock_brd_service):
    mock_brd_service.list_brds = AsyncMock(
        return_value=BrdListResponse.build(
            items=[_make_brd_response()],
            total=1,
            page=1,
            page_size=20,
            status=None,
            search=None,
            file_extension=None,
            has_images=None,
            sort_by="created_at",
            sort_order="desc",
        )
    )

    response = client.get("/api/v1/brds")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["has_next"] is False
    assert body["items"][0]["name"] == "Payments BRD"


def test_get_brd_not_found_returns_404(client, mock_brd_service):
    from fastapi import HTTPException

    mock_brd_service.get_brd = AsyncMock(
        side_effect=HTTPException(status_code=404, detail="BRD not found")
    )

    response = client.get("/api/v1/brds/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "BRD not found"


def test_rename_brd_success(client, mock_brd_service):
    detail = BrdDetailResponse(
        **_make_brd_response(name="Renamed BRD").model_dump(
            exclude={"file_size_mb", "is_ready", "has_parse_error"}
        )
    )
    mock_brd_service.rename_brd = AsyncMock(return_value=detail)

    response = client.patch("/api/v1/brds/1", json={"name": "Renamed BRD"})

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed BRD"
    mock_brd_service.rename_brd.assert_awaited_once_with(1, 1, "Renamed BRD")


def test_rename_brd_rejects_blank_name(client, mock_brd_service):
    response = client.patch("/api/v1/brds/1", json={"name": "   "})
    assert response.status_code == 422


def test_reparse_brd_conflict_when_already_parsing(client, mock_brd_service):
    from fastapi import HTTPException

    mock_brd_service.enqueue_reparse = AsyncMock(
        side_effect=HTTPException(
            status_code=409, detail="This BRD is already being parsed."
        )
    )

    response = client.post("/api/v1/brds/1/reparse")

    assert response.status_code == 409


def test_delete_brd_success(client, mock_brd_service):
    from app.schemas.brd_schema import BrdDeleteResponse

    mock_brd_service.delete_brd = AsyncMock(return_value=BrdDeleteResponse(id=1))

    response = client.delete("/api/v1/brds/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_get_operation_status(client, mock_operation_service):
    mock_operation_service.get_status = AsyncMock(
        return_value=_make_operation_response(status="succeeded", completed_at=NOW)
    )

    response = client.get(
        "/api/v1/brds/status/11111111-1111-1111-1111-111111111111"
    )

    assert response.status_code == 200
    assert response.json()["done"] is True


def test_get_operation_result_conflict_while_running(client, mock_operation_service):
    from fastapi import HTTPException

    mock_operation_service.get_result = AsyncMock(
        side_effect=HTTPException(
            status_code=409, detail={"message": "Operation is still in progress"}
        )
    )

    response = client.get(
        "/api/v1/brds/result/11111111-1111-1111-1111-111111111111"
    )

    assert response.status_code == 409
