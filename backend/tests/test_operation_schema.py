from datetime import datetime, timezone

from app.schemas.operation_schema import OperationResponse


def test_operation_response_urls_and_done_flag():
    now = datetime.now(timezone.utc)
    running = OperationResponse(
        operation_id="11111111-1111-1111-1111-111111111111",
        operation_type="brd_upload",
        status="running",
        resource_type="brd",
        resource_id=42,
        created_at=now,
        updated_at=now,
    )
    assert running.done is False
    assert running.status_url == (
        "/api/v1/brds/status/11111111-1111-1111-1111-111111111111"
    )
    assert running.result_url == (
        "/api/v1/brds/result/11111111-1111-1111-1111-111111111111"
    )

    done = running.model_copy(update={"status": "succeeded"})
    assert done.done is True

    cancelled = running.model_copy(update={"status": "cancelled"})
    assert cancelled.done is True


def test_operation_response_urls_for_feature_extraction():
    now = datetime.now(timezone.utc)
    op = OperationResponse(
        operation_id="22222222-2222-2222-2222-222222222222",
        operation_type="feature_extraction",
        status="running",
        resource_type="brd",
        resource_id=10,
        created_at=now,
        updated_at=now,
    )
    assert op.status_url == (
        "/api/v1/features/status/22222222-2222-2222-2222-222222222222"
    )
    assert op.result_url == (
        "/api/v1/features/result/22222222-2222-2222-2222-222222222222"
    )


def test_operation_response_urls_for_story_generation():
    now = datetime.now(timezone.utc)
    op = OperationResponse(
        operation_id="33333333-3333-3333-3333-333333333333",
        operation_type="story_generation",
        status="pending",
        resource_type="sub_feature",
        resource_id=5,
        created_at=now,
        updated_at=now,
    )
    assert op.status_url == (
        "/api/v1/stories/status/33333333-3333-3333-3333-333333333333"
    )
    assert op.result_url == (
        "/api/v1/stories/result/33333333-3333-3333-3333-333333333333"
    )


def test_operation_response_urls_for_sub_feature_generation():
    now = datetime.now(timezone.utc)
    op = OperationResponse(
        operation_id="44444444-4444-4444-4444-444444444444",
        operation_type="sub_feature_generation",
        status="pending",
        resource_type="feature",
        resource_id=7,
        created_at=now,
        updated_at=now,
    )
    assert op.status_url == (
        "/api/v1/sub-features/status/44444444-4444-4444-4444-444444444444"
    )
    assert op.result_url == (
        "/api/v1/sub-features/result/44444444-4444-4444-4444-444444444444"
    )


def test_operation_response_urls_for_test_case_generation():
    now = datetime.now(timezone.utc)
    op = OperationResponse(
        operation_id="55555555-5555-5555-5555-555555555555",
        operation_type="test_case_generation",
        status="pending",
        resource_type="story",
        resource_id=9,
        created_at=now,
        updated_at=now,
    )
    assert op.status_url == (
        "/api/v1/test-cases/status/55555555-5555-5555-5555-555555555555"
    )
    assert op.result_url == (
        "/api/v1/test-cases/result/55555555-5555-5555-5555-555555555555"
    )
