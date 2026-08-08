"""Backward-compatible helpers for structure chunking tests."""

from __future__ import annotations

from app.ai.chunking.base import ChunkContext
from app.ai.chunking.strategies.structure_strategy import StructureChunkStrategy
from app.ai.chunking.types import BrdChunkDraft
from app.schemas.pipeline_settings_schema import BrdChunkStrategy


def chunk_markdown(
    text: str,
    *,
    level: BrdChunkStrategy,
    max_chunk_chars: int = 6000,
) -> list[BrdChunkDraft]:
    return StructureChunkStrategy(level).build_chunks(
        text,
        context=ChunkContext(max_chunk_chars=max_chunk_chars),
    )
