from pathlib import Path

from app.parsers.models import ParsedDocument


class DocumentParser:
    """
    Base class for BRD file parsers.

    Subclasses implement `supports` and `parse`.
    """

    def supports(self, mime_type: str | None, extension: str) -> bool:
        raise NotImplementedError

    def parse(self, file_path: Path, *, images_dir: Path | None = None) -> ParsedDocument:
        raise NotImplementedError
