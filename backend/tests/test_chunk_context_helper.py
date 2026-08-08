from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.rag.chunk_retrieval import SimilarChunk
from app.services.ai._chunk_context import fetch_brd_chunk_context


@pytest.mark.asyncio
async def test_fetch_brd_chunk_context_formats_hits():
    client = MagicMock()
    repo = MagicMock()
    chunks = [
        SimilarChunk(
            id=1,
            chunk_index=0,
            section_path="Auth",
            heading="Login",
            chunk_kind="section",
            content="Users log in.",
            distance=0.25,
        )
    ]

    with patch(
        "app.services.ai._chunk_context.retrieve_similar_chunks",
        new=AsyncMock(return_value=chunks),
    ):
        text = await fetch_brd_chunk_context(
            client,
            repo,
            brd_id=5,
            query_parts=["Login", "MFA"],
        )

    assert "[Auth]" in text
    assert "Users log in." in text


@pytest.mark.asyncio
async def test_fetch_brd_chunk_context_returns_empty_on_failure():
    client = MagicMock()
    repo = MagicMock()

    with patch(
        "app.services.ai._chunk_context.retrieve_similar_chunks",
        new=AsyncMock(side_effect=RuntimeError("embed failed")),
    ):
        text = await fetch_brd_chunk_context(
            client,
            repo,
            brd_id=5,
            query_parts=["Login"],
        )

    assert text == ""
