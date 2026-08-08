"""Route-level tests for BRD export endpoint."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_export_service
from app.main import app
from app.services.export.service import ExportFile


class _FakeUser:
    id = 1
    email = "dev@example.com"
    is_active = True
    is_admin = False


@pytest.fixture
def mock_export_service():
    return MagicMock()


@pytest.fixture
def client(mock_export_service):
    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    app.dependency_overrides[get_export_service] = lambda: mock_export_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_export_csv_returns_file_download(client, mock_export_service):
    mock_export_service.export_brd = AsyncMock(
        return_value=ExportFile(
            content="\ufeffbrd_name,story_title\nPayments,Login\n".encode("utf-8"),
            filename="payments-brd-export.csv",
            media_type="text/csv; charset=utf-8",
        )
    )

    response = client.post("/api/v1/brds/1/export?format=csv")

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "payments-brd-export.csv" in response.headers["content-disposition"]
    assert b"Payments" in response.content
    mock_export_service.export_brd.assert_awaited_once_with(1, 1, format="csv")


def test_export_defaults_to_csv(client, mock_export_service):
    mock_export_service.export_brd = AsyncMock(
        return_value=ExportFile(
            content=b"header\n",
            filename="export.csv",
            media_type="text/csv; charset=utf-8",
        )
    )

    response = client.post("/api/v1/brds/1/export")

    assert response.status_code == 200
    mock_export_service.export_brd.assert_awaited_once_with(1, 1, format="csv")


def test_export_propagates_no_approved_stories_conflict(client, mock_export_service):
    mock_export_service.export_brd = AsyncMock(
        side_effect=HTTPException(
            status_code=409,
            detail="No approved stories to export. Approve at least one story first.",
        )
    )

    response = client.post("/api/v1/brds/1/export?format=csv")

    assert response.status_code == 409
    assert "No approved stories" in response.json()["detail"]


def test_export_jira_returns_file_download(client, mock_export_service):
    mock_export_service.export_brd = AsyncMock(
        return_value=ExportFile(
            content="\ufeffSummary,Issue Type\nLogin,Story\n".encode("utf-8"),
            filename="payments-brd-jira-import.csv",
            media_type="text/csv; charset=utf-8",
        )
    )

    response = client.post("/api/v1/brds/1/export?format=jira")

    assert response.status_code == 200
    assert "jira-import.csv" in response.headers["content-disposition"]
    mock_export_service.export_brd.assert_awaited_once_with(1, 1, format="jira")


def test_export_propagates_not_found(client, mock_export_service):
    mock_export_service.export_brd = AsyncMock(
        side_effect=HTTPException(status_code=404, detail="BRD not found")
    )

    response = client.post("/api/v1/brds/99/export?format=csv")

    assert response.status_code == 404
