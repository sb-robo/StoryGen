from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.ai.chunking.types import BrdChunkDraft
from app.schemas.pipeline_settings_schema import BrdChunkStrategy

EmbedBatchFn = Callable[[list[str]], Awaitable[list[list[float]]]]


@dataclass
class ChunkContext:
    """Runtime inputs shared across chunking strategies."""

    embed_batch: EmbedBatchFn | None = None
    parser_tables: list | None = None
    max_chunk_chars: int = 6000


class BrdChunkStrategyBase:
    """
    Base class for BRD chunking strategies.

    Subclasses set `strategy` and implement `chunk` / `build_chunks`.
    """

    strategy: BrdChunkStrategy

    async def chunk(self, text: str, *, context: ChunkContext | None = None) -> list[BrdChunkDraft]:
        raise NotImplementedError

    def build_chunks(self, text: str, *, context: ChunkContext | None = None) -> list[BrdChunkDraft]:
        raise NotImplementedError
