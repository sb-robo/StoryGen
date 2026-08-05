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
