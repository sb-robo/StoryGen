from app.parsers.base import DocumentParser
from app.parsers.docling_parser import DoclingParser


class ParserFactory:
    """
    Factory that selects a DocumentParser by MIME type / file extension.

    New parsers can be registered without changing upload orchestration.
    """

    def __init__(self, parsers: list[DocumentParser] | None = None):
        self._parsers = parsers or [DoclingParser()]

    def get_parser(self, mime_type: str | None, extension: str) -> DocumentParser:
        for parser in self._parsers:
            if parser.supports(mime_type, extension):
                return parser
        raise ValueError(
            f"Unsupported BRD format: extension={extension!r}, mime_type={mime_type!r}. "
            "Allowed: PDF, DOCX, XLSX."
        )

    def register(self, parser: DocumentParser) -> None:
        self._parsers.append(parser)
