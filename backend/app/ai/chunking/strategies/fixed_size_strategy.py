from __future__ import annotations

from app.ai.chunking.split_utils import split_oversized
from app.ai.chunking.types import BrdChunkDraft, ChunkKind, reindex_chunks
from app.schemas.pipeline_settings_schema import BrdChunkStrategy

from app.ai.chunking.base import BrdChunkStrategyBase, ChunkContext

DEFAULT_FIXED_CHUNK_CHARS = 1500
DEFAULT_FIXED_OVERLAP_CHARS = 200


class FixedSizeChunkStrategy(BrdChunkStrategyBase):
    """Even-sized sliding-window chunks with paragraph-aware overlap."""

    def __init__(
        self,
        *,
        max_chunk_chars: int = DEFAULT_FIXED_CHUNK_CHARS,
        overlap_chars: int = DEFAULT_FIXED_OVERLAP_CHARS,
    ):
        self._max_chunk_chars = max_chunk_chars
        self._overlap_chars = overlap_chars

    @property
    def strategy(self) -> BrdChunkStrategy:
        return BrdChunkStrategy.FIXED_SIZE

    def build_chunks(self, text: str, *, context: ChunkContext | None = None) -> list[BrdChunkDraft]:
        ctx = context or ChunkContext()
        max_chars = ctx.max_chunk_chars or self._max_chunk_chars
        stripped = text.strip()
        if not stripped:
            return []

        parts = split_oversized(
            stripped,
            max_chars=max_chars,
            overlap=self._overlap_chars,
        )
        drafts = [
            BrdChunkDraft(
                chunk_index=idx,
                heading=f"Part {idx + 1}",
                heading_depth=None,
                section_path=f"Fixed window > Part {idx + 1}",
                content=piece,
                char_count=len(piece),
                chunk_kind=ChunkKind.FIXED_WINDOW,
            )
            for idx, piece in enumerate(parts)
        ]
        return reindex_chunks(drafts)

    async def chunk(self, text: str, *, context: ChunkContext | None = None) -> list[BrdChunkDraft]:
        return self.build_chunks(text, context=context)
