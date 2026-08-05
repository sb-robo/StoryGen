from pathlib import Path

import pytest

from app.parsers.base import DocumentParser
from app.parsers.docling_parser import DoclingParser
from app.parsers.factory import ParserFactory
from app.parsers.models import ParsedDocument


class StubParser(DocumentParser):
    def supports(self, mime_type: str | None, extension: str) -> bool:
        return extension.lower() in {".txt", "txt"}

    def parse(self, file_path: Path, *, images_dir: Path | None = None) -> ParsedDocument:
        return ParsedDocument(text=file_path.read_text(encoding="utf-8"))


def test_factory_selects_docling_for_pdf():
    factory = ParserFactory([DoclingParser()])
    parser = factory.get_parser("application/pdf", ".pdf")
    assert isinstance(parser, DoclingParser)


def test_factory_selects_docling_for_docx_and_xlsx():
    factory = ParserFactory([DoclingParser()])
    assert isinstance(factory.get_parser(None, ".docx"), DoclingParser)
    assert isinstance(factory.get_parser(None, "xlsx"), DoclingParser)


def test_factory_rejects_unsupported_extension():
    factory = ParserFactory([DoclingParser()])
    with pytest.raises(ValueError, match="Unsupported BRD format"):
        factory.get_parser("text/plain", ".txt")


def test_factory_uses_registered_custom_parser():
    factory = ParserFactory([StubParser()])
    parser = factory.get_parser("text/plain", ".txt")
    assert isinstance(parser, StubParser)
