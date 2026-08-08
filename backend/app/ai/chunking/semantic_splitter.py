from __future__ import annotations

import math
import re
from collections.abc import Awaitable, Callable

from app.ai.chunking.split_utils import split_oversized
from app.ai.chunking.types import BrdChunkDraft, ChunkKind

EmbedBatchFn = Callable[[list[str]], Awaitable[list[list[float]]]]

DEFAULT_SEMANTIC_THRESHOLD_CHARS = 3000
DEFAULT_SIMILARITY_THRESHOLD = 0.72


class SemanticSplitter:
    """Cluster paragraphs by embedding similarity for semantic sub-chunks."""

    def __init__(
        self,
        embed_batch: EmbedBatchFn,
        *,
        threshold_chars: int = DEFAULT_SEMANTIC_THRESHOLD_CHARS,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ):
        self._embed_batch = embed_batch
        self._threshold_chars = threshold_chars
        self._similarity_threshold = similarity_threshold

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _paragraphs(text: str) -> list[str]:
        parts = [part.strip() for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]
        return parts or ([text.strip()] if text.strip() else [])

    async def split_text(self, text: str) -> list[str]:
        stripped = text.strip()
        if len(stripped) <= self._threshold_chars:
            return [stripped]

        paragraphs = self._paragraphs(stripped)
        if len(paragraphs) <= 1:
            return split_oversized(stripped, max_chars=self._threshold_chars)

        vectors = await self._embed_batch(paragraphs)
        groups: list[list[str]] = [[paragraphs[0]]]
        for idx in range(1, len(paragraphs)):
            similarity = self._cosine_similarity(vectors[idx - 1], vectors[idx])
            if similarity >= self._similarity_threshold:
                groups[-1].append(paragraphs[idx])
            else:
                groups.append([paragraphs[idx]])

        chunks = ["\n\n".join(group).strip() for group in groups if group]
        final: list[str] = []
        for chunk in chunks:
            if len(chunk) > self._threshold_chars:
                final.extend(split_oversized(chunk, max_chars=self._threshold_chars))
            else:
                final.append(chunk)
        return final or [stripped]

    async def child_drafts(
        self,
        text: str,
        *,
        parent_chunk_index: int,
        section_path: str,
        heading: str | None,
    ) -> list[BrdChunkDraft]:
        parts = await self.split_text(text)
        if len(parts) <= 1:
            return []

        drafts: list[BrdChunkDraft] = []
        for offset, piece in enumerate(parts):
            drafts.append(
                BrdChunkDraft(
                    chunk_index=offset,
                    heading=heading,
                    heading_depth=None,
                    section_path=f"{section_path} > Part {offset + 1}",
                    content=piece,
                    char_count=len(piece),
                    chunk_kind=ChunkKind.SEMANTIC_PART,
                    parent_chunk_index=parent_chunk_index,
                )
            )
        return drafts
