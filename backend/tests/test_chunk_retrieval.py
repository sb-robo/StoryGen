from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.rag.chunk_retrieval import (
    SimilarChunk,
    build_retrieval_query,
    format_similar_chunks,
    retrieve_similar_chunks,
)
from app.repositories.brd_chunk_repository import SimilarChunkRow


def test_format_similar_chunks_empty():
    assert format_similar_chunks([]) == "(no relevant BRD sections retrieved)"


def test_format_similar_chunks_includes_path_and_similarity():
    chunks = [
        SimilarChunk(
            id=1,
            chunk_index=0,
            section_path="Auth > Login",
            heading="Login",
            chunk_kind="section",
            content="Users authenticate with email and password.",
            distance=0.2,
        )
    ]
    formatted = format_similar_chunks(chunks)
    assert "[Auth > Login]" in formatted
    assert "similarity=0.80" in formatted
    assert "Users authenticate" in formatted


def test_build_retrieval_query_skips_blanks():
    assert build_retrieval_query("Login", None, "  ", "MFA required") == "Login\nMFA required"


@pytest.mark.asyncio
async def test_retrieve_similar_chunks_embeds_and_queries_repo():
    client = MagicMock()
    client.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
    repo = MagicMock()
    repo.find_similar = AsyncMock(
        return_value=[
            SimilarChunkRow(
                id=9,
                chunk_index=2,
                section_path="Billing",
                heading="Invoices",
                chunk_kind="section",
                content="Invoice PDF export",
                distance=0.15,
            )
        ]
    )

    results = await retrieve_similar_chunks(
        client,
        repo,
        brd_id=42,
        query_text="billing invoices",
        limit=3,
    )

    client.embed_text.assert_awaited_once_with("billing invoices")
    repo.find_similar.assert_awaited_once_with(42, [0.1, 0.2, 0.3], limit=3)
    assert len(results) == 1
    assert results[0].id == 9
    assert results[0].section_path == "Billing"


@pytest.mark.asyncio
async def test_retrieve_similar_chunks_empty_query_skips_embed():
    client = MagicMock()
    client.embed_text = AsyncMock()
    repo = MagicMock()
    repo.find_similar = AsyncMock()

    results = await retrieve_similar_chunks(
        client, repo, brd_id=1, query_text="   "
    )

    assert results == []
    client.embed_text.assert_not_awaited()
    repo.find_similar.assert_not_awaited()
