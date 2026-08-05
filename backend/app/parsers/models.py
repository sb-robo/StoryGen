from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class TableBlock:
    """Structured table extracted from a BRD document."""

    index: int
    markdown: str
    row_count: int = 0
    column_count: int = 0


@dataclass(slots=True)
class ImageAsset:
    """Image extracted from a BRD and saved under the BRD storage folder."""

    index: int
    filename: str
    relative_path: str
    caption: str | None = None


@dataclass(slots=True)
class ParsedDocument:
    """Normalized parser output used by the BRD pipeline."""

    text: str
    tables: list[TableBlock] = field(default_factory=list)
    images: list[ImageAsset] = field(default_factory=list)
    page_count: int | None = None
    metadata: dict = field(default_factory=dict)

    def write_markdown(self, path: Path) -> None:
        path.write_text(self.text, encoding="utf-8")
