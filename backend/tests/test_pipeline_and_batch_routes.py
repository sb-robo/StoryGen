"""Route tests for pipeline-summary and batch generate-all endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import (
    get_batch_service,
    get_current_user,
    get_pipeline_service,
)
from app.main import app
from app.schemas.batch_schema import BatchOperationResponse
from app.schemas.operation_schema import OperationResponse
from app.schemas.pipeline_schema import (
    PipelineSummaryResponse,
    PipelineTotals,
    PipelineTreeResponse,
    StageSummary,
    StatusCounts,
    SuggestedStep,
)

NOW = datetime.now(timezone.utc)


class _FakeUser:
    id = 1
    email = "dev@example.com"
    is_active = True
    is_admin = False


@pytest.fixture
def mock_pipeline_service():
    return MagicMock()


@pytest.fixture
def mock_batch_service():
    return MagicMock()


@pytest.fixture
def client(mock_pipeline_service, mock_batch_service):
    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline_service
    app.dependency_overrides[get_batch_service] = lambda: mock_batch_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_pipeline_summary_ok(client, mock_pipeline_service):
    mock_pipeline_service.get_summary = AsyncMock(
        return_value=PipelineSummaryResponse(
            brd_id=1,
            brd_status="parsed",
            stages={
                "features": StageSummary(
                    id="features",
                    status="needs_review",
                    counts=StatusCounts(total=2, approved=1, pending_review=1),
                    pending=1,
                )
            },
            blockers=[],
            suggested_step=SuggestedStep(
                label="Review 1 pending item",
                action="review",
                stage_id="features",
            ),
            totals=PipelineTotals(pending_review=1, approved_stories=0),
        )
    )

    response = client.get("/api/v1/brds/1/pipeline-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["brd_id"] == 1
    assert body["suggested_step"]["action"] == "review"
    mock_pipeline_service.get_summary.assert_awaited_once_with(1, 1)


def test_pipeline_tree_ok(client, mock_pipeline_service):
    mock_pipeline_service.get_tree = AsyncMock(
        return_value=PipelineTreeResponse(
            brd_id=1,
            features=[],
            sub_features=[],
            stories=[],
            test_cases=[],
        )
    )

    response = client.get("/api/v1/brds/1/pipeline")

    assert response.status_code == 200
    body = response.json()
    assert body["brd_id"] == 1
    assert body["features"] == []
    assert body["sub_features"] == []
    mock_pipeline_service.get_tree.assert_awaited_once_with(1, 1)


def test_batch_sub_features_returns_202(client, mock_batch_service):
    op = OperationResponse(
        operation_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        operation_type="sub_feature_generation",
        status="pending",
        resource_type="feature",
        resource_id=10,
        error_message=None,
        created_at=NOW,
        updated_at=NOW,
        completed_at=None,
    )
    mock_batch_service.enqueue_sub_features_all = AsyncMock(
        return_value=(
            BatchOperationResponse(
                brd_id=1,
                action="sub_features",
                operations=[op],
                total=1,
                skipped=[],
            ),
            [op.operation_id],
        )
    )

    response = client.post("/api/v1/brds/1/sub-features/generate-all")

    assert response.status_code == 202
    body = response.json()
    assert body["total"] == 1
    assert body["operations"][0]["operation_id"] == op.operation_id
