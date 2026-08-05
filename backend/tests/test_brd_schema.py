from datetime import datetime, timezone

from app.schemas.brd_schema import BrdResponse


def test_brd_response_computed_flags():
    now = datetime.now(timezone.utc)
    parsed = BrdResponse(
        id=1,
        user_id=2,
        name="Payments Platform BRD",
        original_filename="spec.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size_bytes=2_097_152,
        status="parsed",
        created_at=now,
        updated_at=now,
    )
    assert parsed.is_ready is True
    assert parsed.has_parse_error is False
    assert parsed.file_size_mb == 2.0

    failed = parsed.model_copy(update={"status": "parse_failed"})
    assert failed.is_ready is False
    assert failed.has_parse_error is True
