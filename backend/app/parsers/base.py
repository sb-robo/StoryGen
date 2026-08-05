from abc import ABC, abstractmethod
from pathlib import Path

from app.parsers.models import ParsedDocument


class DocumentParser(ABC):
    """Strategy interface for converting an uploaded BRD file into structured text."""

    @abstractmethod
    def supports(self, mime_type: str | None, extension: str) -> bool:
        """Return True when this parser can handle the given file type."""

    @abstractmethod
    def parse(self, file_path: Path, *, images_dir: Path | None = None) -> ParsedDocument:
        """
        Parse `file_path` into a `ParsedDocument`.

        When `images_dir` is provided, extracted images should be written there
        and referenced from `ParsedDocument.images`.
        """
