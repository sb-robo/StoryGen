from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureExtractionContext:
    """Prepared BRD text and structure hints for feature extraction."""

    brd_content: str
    section_hints: str
    source: str  # "chunks" | "retrieved_chunks" | "full_document"
    chunk_count: int = 0

    @property
    def uses_chunks(self) -> bool:
        return self.source in {"chunks", "retrieved_chunks"}
