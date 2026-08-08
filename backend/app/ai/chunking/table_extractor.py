from __future__ import annotations

import re

from app.ai.chunking.types import BrdChunkDraft, ChunkKind


class TableExtractor:
    """Extract markdown tables as standalone chunk drafts."""

    _TABLE_BLOCK_RE = re.compile(
        r"(?:^|\n)(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)*)",
        re.MULTILINE,
    )

    def extract_from_markdown(self, text: str) -> tuple[str, list[str]]:
        tables = [match.group(1).strip() for match in self._TABLE_BLOCK_RE.finditer(text)]
        prose = self._TABLE_BLOCK_RE.sub("\n\n", text)
        prose = re.sub(r"\n{3,}", "\n\n", prose).strip()
        return prose, tables

    def drafts_from_markdown(
        self,
        text: str,
        *,
        start_index: int,
        parent_chunk_index: int | None,
        section_path: str,
    ) -> tuple[str, list[BrdChunkDraft]]:
        prose, tables = self.extract_from_markdown(text)
        drafts: list[BrdChunkDraft] = []
        for offset, table_md in enumerate(tables):
            label = f"Table {offset + 1}"
            drafts.append(
                BrdChunkDraft(
                    chunk_index=start_index + offset,
                    heading=label,
                    heading_depth=None,
                    section_path=f"{section_path} > {label}",
                    content=table_md,
                    char_count=len(table_md),
                    chunk_kind=ChunkKind.TABLE,
                    parent_chunk_index=parent_chunk_index,
                )
            )
        return prose, drafts

    def drafts_from_parser_tables(
        self,
        tables: list,
        *,
        start_index: int,
        section_path: str = "Document > Extracted tables",
    ) -> list[BrdChunkDraft]:
        drafts: list[BrdChunkDraft] = []
        for offset, table in enumerate(tables):
            markdown = getattr(table, "markdown", None) or (
                table.get("markdown") if isinstance(table, dict) else str(table)
            )
            markdown = (markdown or "").strip()
            if not markdown:
                continue
            label = f"Table {offset + 1}"
            drafts.append(
                BrdChunkDraft(
                    chunk_index=start_index + offset,
                    heading=label,
                    heading_depth=None,
                    section_path=f"{section_path} > {label}",
                    content=markdown,
                    char_count=len(markdown),
                    chunk_kind=ChunkKind.TABLE,
                    parent_chunk_index=None,
                )
            )
        return drafts
