from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ChunkKind(StrEnum):
    SECTION = "section"
    REQUIREMENT = "requirement"
    TABLE = "table"
    FIXED_WINDOW = "fixed_window"
    SEMANTIC_PART = "semantic_part"


@dataclass(frozen=True)
class BrdChunkDraft:
    chunk_index: int
    heading: str | None
    heading_depth: int | None
    section_path: str
    content: str
    char_count: int
    chunk_kind: ChunkKind = ChunkKind.SECTION
    parent_chunk_index: int | None = None


def reindex_chunks(drafts: list[BrdChunkDraft]) -> list[BrdChunkDraft]:
    return [
        BrdChunkDraft(
            chunk_index=idx,
            heading=draft.heading,
            heading_depth=draft.heading_depth,
            section_path=draft.section_path,
            content=draft.content,
            char_count=draft.char_count,
            chunk_kind=draft.chunk_kind,
            parent_chunk_index=draft.parent_chunk_index,
        )
        for idx, draft in enumerate(drafts)
    ]
