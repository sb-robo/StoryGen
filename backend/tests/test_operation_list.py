from datetime import datetime, timezone

from app.schemas.operation_schema import OperationListResponse, OperationResponse


def test_operation_list_response_pagination_math():
    now = datetime.now(timezone.utc)
    item = OperationResponse(
        operation_id="11111111-1111-1111-1111-111111111111",
        operation_type="brd_upload",
        status="succeeded",
        resource_type="brd",
        resource_id=1,
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    page1 = OperationListResponse.build(
        items=[item],
        total=45,
        page=1,
        page_size=20,
        status=None,
        operation_type=None,
        resource_type=None,
        resource_id=None,
        sort_by="created_at",
        sort_order="desc",
    )
    assert page1.total_pages == 3
    assert page1.has_next is True
    assert page1.has_prev is False

    page3 = OperationListResponse.build(
        items=[item],
        total=45,
        page=3,
        page_size=20,
        status="succeeded",
        operation_type="brd_upload",
        resource_type="brd",
        resource_id=1,
        sort_by="created_at",
        sort_order="desc",
    )
    assert page3.has_next is False
    assert page3.has_prev is True
