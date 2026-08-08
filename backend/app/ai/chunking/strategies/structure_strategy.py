from __future__ import annotations

import re

from app.ai.chunking.split_utils import split_oversized
from app.ai.chunking.types import BrdChunkDraft, ChunkKind
from app.schemas.pipeline_settings_schema import BrdChunkStrategy

from app.ai.chunking.base import BrdChunkStrategyBase, ChunkContext

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class StructureChunkStrategy(BrdChunkStrategyBase):
    """Split markdown at heading boundaries (section or subsection depth)."""

    def __init__(self, strategy: BrdChunkStrategy):
        if strategy not in (BrdChunkStrategy.SECTION, BrdChunkStrategy.SUBSECTION):
            raise ValueError(f"StructureChunkStrategy does not support {strategy!r}")
        self._strategy = strategy

    @property
    def strategy(self) -> BrdChunkStrategy:
        return self._strategy

    def _max_heading_depth(self) -> int:
        return 2 if self._strategy == BrdChunkStrategy.SECTION else 3

    def build_chunks(self, text: str, *, context: ChunkContext | None = None) -> list[BrdChunkDraft]:
        ctx = context or ChunkContext()
        max_depth = self._max_heading_depth()
        lines = text.splitlines()
        blocks: list[dict] = []
        path_stack: list[tuple[int, str]] = []
        current: dict = {"heading": None, "depth": None, "lines": [], "path": []}

        def flush_block() -> None:
            if not current["lines"]:
                return
            blocks.append(
                {
                    "heading": current["heading"],
                    "depth": current["depth"],
                    "lines": list(current["lines"]),
                    "path": list(current["path"]),
                }
            )

        for line in lines:
            match = _HEADING_RE.match(line)
            if match and len(match.group(1)) <= max_depth:
                flush_block()
                depth = len(match.group(1))
                title = match.group(2).strip()
                while path_stack and path_stack[-1][0] >= depth:
                    path_stack.pop()
                path_stack.append((depth, title))
                current = {
                    "heading": title,
                    "depth": depth,
                    "lines": [line],
                    "path": [part for _, part in path_stack],
                }
                continue

            if not blocks and current["heading"] is None and not current["lines"]:
                current["path"] = ["Preamble"]
            current["lines"].append(line)

        flush_block()

        if not blocks and text.strip():
            blocks.append({"heading": None, "depth": None, "lines": lines, "path": ["Document"]})

        drafts: list[BrdChunkDraft] = []
        chunk_index = 0
        for block in blocks:
            body = "\n".join(block["lines"]).strip()
            if not body:
                continue
            section_path = " > ".join(block["path"]) if block["path"] else "Document"
            for piece in split_oversized(body, max_chars=ctx.max_chunk_chars):
                drafts.append(
                    BrdChunkDraft(
                        chunk_index=chunk_index,
                        heading=block["heading"],
                        heading_depth=block["depth"],
                        section_path=section_path,
                        content=piece,
                        char_count=len(piece),
                        chunk_kind=ChunkKind.SECTION,
                    )
                )
                chunk_index += 1

        return drafts

    async def chunk(self, text: str, *, context: ChunkContext | None = None) -> list[BrdChunkDraft]:
        return self.build_chunks(text, context=context)
