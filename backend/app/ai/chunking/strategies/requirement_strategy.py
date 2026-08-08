from __future__ import annotations

import re

from app.ai.chunking.split_utils import split_oversized
from app.ai.chunking.types import BrdChunkDraft, ChunkKind, reindex_chunks
from app.schemas.pipeline_settings_schema import BrdChunkStrategy

from app.ai.chunking.base import BrdChunkStrategyBase, ChunkContext

_REQUIREMENT_START_RE = re.compile(
    r"^("
    r"(?:REQ|FR|US|BRD|NFR|AC)[-_ ]?\d+(?:\.\d+)*"
    r"|\d+(?:\.\d+)+\s+\S"
    r"|\d+\.\s+\S"
    r")",
    re.IGNORECASE,
)
_SHALL_LINE_RE = re.compile(r"\b(shall|must)\b", re.IGNORECASE)


class RequirementChunkStrategy(BrdChunkStrategyBase):
    """Split on numbered requirements and shall/must bullet items."""

    @property
    def strategy(self) -> BrdChunkStrategy:
        return BrdChunkStrategy.REQUIREMENT

    @staticmethod
    def _is_requirement_start(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if _REQUIREMENT_START_RE.match(stripped):
            return True
        return bool(stripped.startswith(("-", "*", "•")) and _SHALL_LINE_RE.search(stripped))

    @staticmethod
    def _requirement_label(line: str) -> str:
        stripped = line.strip()
        match = _REQUIREMENT_START_RE.match(stripped)
        if match:
            return match.group(1).strip()
        return stripped[:80]

    def build_chunks(self, text: str, *, context: ChunkContext | None = None) -> list[BrdChunkDraft]:
        ctx = context or ChunkContext()
        lines = text.splitlines()
        blocks: list[dict] = []
        current: dict = {"label": None, "lines": []}

        def flush() -> None:
            if not current["lines"]:
                return
            blocks.append({"label": current["label"], "lines": list(current["lines"])})
            current["label"] = None
            current["lines"] = []

        for line in lines:
            if self._is_requirement_start(line):
                flush()
                current["label"] = self._requirement_label(line)
                current["lines"] = [line]
                continue
            if not blocks and current["label"] is None and not current["lines"] and line.strip():
                current["label"] = "Preamble"
            current["lines"].append(line)

        flush()

        if not blocks and text.strip():
            blocks.append({"label": "Document", "lines": lines})

        drafts: list[BrdChunkDraft] = []
        for block in blocks:
            body = "\n".join(block["lines"]).strip()
            if not body:
                continue
            label = block["label"] or "Requirement"
            section_path = f"Requirements > {label}"
            for piece in split_oversized(body, max_chars=ctx.max_chunk_chars):
                drafts.append(
                    BrdChunkDraft(
                        chunk_index=len(drafts),
                        heading=label,
                        heading_depth=None,
                        section_path=section_path,
                        content=piece,
                        char_count=len(piece),
                        chunk_kind=ChunkKind.REQUIREMENT,
                    )
                )

        return reindex_chunks(drafts)

    async def chunk(self, text: str, *, context: ChunkContext | None = None) -> list[BrdChunkDraft]:
        return self.build_chunks(text, context=context)
