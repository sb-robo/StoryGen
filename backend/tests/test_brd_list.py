from datetime import datetime, timezone

from app.schemas.brd_schema import BrdListResponse, BrdResponse


def test_brd_list_response_pagination_math():
    now = datetime.now(timezone.utc)
    item = BrdResponse(
        id=1,
        user_id=2,
        name="Payments BRD",
        original_filename="spec.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size_bytes=1024,
        status="parsed",
        created_at=now,
        updated_at=now,
    )
    page1 = BrdListResponse.build(
        items=[item],
        total=45,
        page=1,
        page_size=20,
        status=None,
        search=None,
        file_extension=None,
        has_images=None,
        sort_by="created_at",
        sort_order="desc",
    )
    assert page1.total_pages == 3
    assert page1.has_next is True
    assert page1.has_prev is False

    page3 = BrdListResponse.build(
        items=[item],
        total=45,
        page=3,
        page_size=20,
        status="parsed",
        search="pay",
        file_extension=".pdf",
        has_images=True,
        sort_by="name",
        sort_order="asc",
    )
    assert page3.has_next is False
    assert page3.has_prev is True
