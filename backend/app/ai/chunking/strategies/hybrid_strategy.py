from __future__ import annotations

from app.ai.chunking.semantic_splitter import DEFAULT_SEMANTIC_THRESHOLD_CHARS, SemanticSplitter
from app.ai.chunking.strategies.structure_strategy import StructureChunkStrategy
from app.ai.chunking.table_extractor import TableExtractor
from app.ai.chunking.types import BrdChunkDraft, reindex_chunks
from app.schemas.pipeline_settings_schema import BrdChunkStrategy

from app.ai.chunking.base import BrdChunkStrategyBase, ChunkContext


class HybridChunkStrategy(BrdChunkStrategyBase):
    """
    Composite strategy: section split → inline tables → semantic split → parser tables.
    """

    def __init__(self) -> None:
        self._structure = StructureChunkStrategy(BrdChunkStrategy.SECTION)
        self._tables = TableExtractor()

    @property
    def strategy(self) -> BrdChunkStrategy:
        return BrdChunkStrategy.HYBRID

    async def chunk(self, text: str, *, context: ChunkContext | None = None) -> list[BrdChunkDraft]:
        ctx = context or ChunkContext()
        section_drafts = await self._structure.chunk(text, context=ctx)
        expanded: list[BrdChunkDraft] = []

        for draft in section_drafts:
            parent_index = len(expanded)
            prose, table_drafts = self._tables.drafts_from_markdown(
                draft.content,
                start_index=parent_index + 1,
                parent_chunk_index=parent_index,
                section_path=draft.section_path,
            )
            parent = BrdChunkDraft(
                chunk_index=parent_index,
                heading=draft.heading,
                heading_depth=draft.heading_depth,
                section_path=draft.section_path,
                content=prose or draft.content,
                char_count=len(prose or draft.content),
                chunk_kind=draft.chunk_kind,
                parent_chunk_index=draft.parent_chunk_index,
            )
            expanded.append(parent)

            for table in table_drafts:
                expanded.append(
                    BrdChunkDraft(
                        chunk_index=len(expanded),
                        heading=table.heading,
                        heading_depth=table.heading_depth,
                        section_path=table.section_path,
                        content=table.content,
                        char_count=table.char_count,
                        chunk_kind=table.chunk_kind,
                        parent_chunk_index=parent_index,
                    )
                )

            if ctx.embed_batch is not None and len(parent.content) > DEFAULT_SEMANTIC_THRESHOLD_CHARS:
                splitter = SemanticSplitter(ctx.embed_batch)
                children = await splitter.child_drafts(
                    parent.content,
                    parent_chunk_index=parent_index,
                    section_path=parent.section_path,
                    heading=parent.heading,
                )
                for child in children:
                    expanded.append(
                        BrdChunkDraft(
                            chunk_index=len(expanded),
                            heading=child.heading,
                            heading_depth=child.heading_depth,
                            section_path=child.section_path,
                            content=child.content,
                            char_count=child.char_count,
                            chunk_kind=child.chunk_kind,
                            parent_chunk_index=parent_index,
                        )
                    )

        if ctx.parser_tables:
            for table in self._tables.drafts_from_parser_tables(
                ctx.parser_tables,
                start_index=len(expanded),
                section_path="Document > Extracted tables",
            ):
                expanded.append(
                    BrdChunkDraft(
                        chunk_index=len(expanded),
                        heading=table.heading,
                        heading_depth=table.heading_depth,
                        section_path=table.section_path,
                        content=table.content,
                        char_count=table.char_count,
                        chunk_kind=table.chunk_kind,
                        parent_chunk_index=table.parent_chunk_index,
                    )
                )

        return reindex_chunks(expanded)
