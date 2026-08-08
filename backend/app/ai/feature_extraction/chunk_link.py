"""Resolve LLM section paths to brd_chunks.id for provenance."""

from __future__ import annotations

from app.db.models.brd_chunk import BrdChunk


def resolve_source_chunk_id(
    chunks: list[BrdChunk],
    *,
    section_path: str | None,
    source_excerpt: str | None = None,
) -> int | None:
    """
    Map a model-provided section path (or excerpt) to a chunk id.

    Prefer exact section_path match, then case-insensitive, then excerpt containment.
    """
    if not chunks:
        return None

    path = (section_path or "").strip()
    if path:
        for chunk in chunks:
            if chunk.section_path == path:
                return chunk.id
        lowered = path.lower()
        for chunk in chunks:
            if chunk.section_path.lower() == lowered:
                return chunk.id
        for chunk in chunks:
            if lowered in chunk.section_path.lower() or chunk.section_path.lower() in lowered:
                return chunk.id

    excerpt = (source_excerpt or "").strip()
    if excerpt and len(excerpt) >= 12:
        needle = excerpt[:80].lower()
        for chunk in chunks:
            if needle in (chunk.content or "").lower():
                return chunk.id
            if needle in (chunk.section_path or "").lower():
                return chunk.id

    return None
