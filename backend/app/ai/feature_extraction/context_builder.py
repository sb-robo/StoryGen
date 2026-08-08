from __future__ import annotations

from collections import OrderedDict

from app.ai.feature_extraction.context import FeatureExtractionContext
from app.ai.rag.chunk_retrieval import SimilarChunk, format_similar_chunks
from app.core.config import settings
from app.db.models.brd_chunk import BrdChunk
from app.repositories.brd_chunk_repository import BrdChunkRepository
from app.services.brd.storage_service import BrdStorageService

MAP_REDUCE_CHUNK_THRESHOLD = 6


class FeatureExtractionContextBuilder:
    """Build feature-extraction input from indexed chunks or full parsed markdown."""

    def __init__(
        self,
        chunk_repo: BrdChunkRepository,
        storage: BrdStorageService | None = None,
    ):
        self.chunk_repo = chunk_repo
        self.storage = storage or BrdStorageService()

    async def build(self, brd) -> FeatureExtractionContext:
        chunks = await self.chunk_repo.list_for_brd(brd.id)
        if chunks:
            return FeatureExtractionContext(
                brd_content=self._format_chunks(chunks),
                section_hints=self._section_hints_from_chunks(chunks),
                source="chunks",
                chunk_count=len(chunks),
            )

        text = await self.storage.read_parsed_markdown(brd.parsed_text_path)
        if not text:
            raise RuntimeError("Parsed BRD content is not available")

        return FeatureExtractionContext(
            brd_content=text,
            section_hints=self._section_hints_from_text(text),
            source="full_document",
            chunk_count=0,
        )

    def build_from_retrieved(
        self,
        retrieved: list[SimilarChunk],
        *,
        total_chunk_count: int,
        section_hints: str,
    ) -> FeatureExtractionContext:
        return FeatureExtractionContext(
            brd_content=format_similar_chunks(
                retrieved,
                empty_message="(no relevant BRD chunks retrieved)",
            ),
            section_hints=section_hints,
            source="retrieved_chunks",
            chunk_count=total_chunk_count,
        )

    def group_chunks_by_section(self, chunks: list[BrdChunk]) -> list[tuple[str, list[BrdChunk]]]:
        groups: OrderedDict[str, list[BrdChunk]] = OrderedDict()
        for chunk in chunks:
            top_level = chunk.section_path.split(" > ", 1)[0]
            groups.setdefault(top_level, []).append(chunk)
        return list(groups.items())

    def should_map_reduce(self, context: FeatureExtractionContext, chunks: list[BrdChunk]) -> bool:
        return (
            context.source == "chunks"
            and len(chunks) > MAP_REDUCE_CHUNK_THRESHOLD
        )

    def should_use_retrieval(self, context: FeatureExtractionContext) -> bool:
        """Prefer vector top-k when the BRD has many indexed chunks with embeddings."""
        return (
            context.uses_chunks
            and context.chunk_count > settings.RAG_FEATURE_RETRIEVAL_THRESHOLD
        )

    def format_chunk_group(self, section: str, chunks: list[BrdChunk]) -> str:
        return self._format_chunks(chunks, group_label=section)

    @staticmethod
    def _format_chunks(chunks: list[BrdChunk], *, group_label: str | None = None) -> str:
        parts: list[str] = []
        if group_label:
            parts.append(f"# Section group: {group_label}\n")
        for chunk in chunks:
            header = f"### [{chunk.section_path}]"
            if chunk.heading:
                header += f" — {chunk.heading}"
            if chunk.chunk_kind != "section":
                header += f" ({chunk.chunk_kind})"
            parts.append(f"{header}\n{chunk.content.strip()}")
        return "\n\n".join(parts)

    @staticmethod
    def _section_hints_from_chunks(chunks: list[BrdChunk], *, max_items: int = 40) -> str:
        seen: OrderedDict[str, None] = OrderedDict()
        for chunk in chunks:
            seen.setdefault(chunk.section_path, None)
            if len(seen) >= max_items:
                break
        if not seen:
            return "(no indexed sections found)"
        return "\n".join(f"- {path}" for path in seen)

    @staticmethod
    def _section_hints_from_text(text: str, *, max_lines: int = 40) -> str:
        import re

        headings: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                headings.append(stripped.lstrip("#").strip())
            elif re.match(r"^\d+(\.\d+)*\s+\S", stripped):
                headings.append(stripped)
            if len(headings) >= max_lines:
                break
        return "\n".join(headings) if headings else "(no clear headings found)"
