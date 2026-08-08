from unittest.mock import MagicMock

from app.ai.feature_extraction.chunk_link import resolve_source_chunk_id
from app.ai.feature_extraction.constraints import format_existing_feature_constraints


def test_resolve_source_chunk_id_exact_path():
    chunk = MagicMock()
    chunk.id = 11
    chunk.section_path = "Auth > Login"
    chunk.content = "Users log in"
    assert (
        resolve_source_chunk_id([chunk], section_path="Auth > Login", source_excerpt=None)
        == 11
    )


def test_resolve_source_chunk_id_from_excerpt():
    chunk = MagicMock()
    chunk.id = 22
    chunk.section_path = "Billing"
    chunk.content = "Invoice PDF export is available nightly."
    assert (
        resolve_source_chunk_id(
            [chunk],
            section_path=None,
            source_excerpt="Invoice PDF export is available",
        )
        == 22
    )


def test_format_existing_feature_constraints():
    text = format_existing_feature_constraints(
        [("Auth", "Login capability")],
        edited_pending=[("Billing", "User edited billing scope")],
    )
    assert "EXISTING APPROVED FEATURES" in text
    assert "Auth" in text
    assert "USER-EDITED DRAFT FEATURES" in text
