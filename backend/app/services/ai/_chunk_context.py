"""Shared helper to ground AI stages with retrieved BRD chunks."""

from __future__ import annotations

from app.ai.openai_client import OpenAIClient
from app.ai.rag.chunk_retrieval import (
    build_retrieval_query,
    format_similar_chunks,
    retrieve_similar_chunks,
)
from app.repositories.brd_chunk_repository import BrdChunkRepository
from app.utils.process_tracker import track, track_error


async def fetch_brd_chunk_context(
    client: OpenAIClient,
    chunk_repo: BrdChunkRepository,
    *,
    brd_id: int,
    query_parts: list[str | None],
) -> str:
    """
    Retrieve top-k BRD chunks for a stage query.

    Returns a formatted prompt block, or empty string when retrieval is unavailable
    (no embeddings / embed failure / empty query) so callers keep working.
    """
    query = build_retrieval_query(*query_parts)
    if not query:
        track("skipped (empty query)", brd_id=brd_id)
        return ""

    track("search similar BRD chunks", brd_id=brd_id)
    try:
        chunks = await retrieve_similar_chunks(
            client,
            chunk_repo,
            brd_id=brd_id,
            query_text=query,
        )
    except Exception as exc:
        track_error(
            "retrieval failed; continuing without chunk context",
            exc=exc,
            brd_id=brd_id,
        )
        return ""

    if not chunks:
        track("no similar chunks found", brd_id=brd_id)
        return ""
    track("chunks retrieved", brd_id=brd_id, count=len(chunks))
    return format_similar_chunks(chunks)
