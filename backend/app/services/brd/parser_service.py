import asyncio
from pathlib import Path

from app.parsers.base import DocumentParser
from app.parsers.factory import ParserFactory
from app.parsers.models import ParsedDocument
from app.services.brd.storage_service import BrdStorageService


class BrdParserService:
    """Orchestrates DocumentParser selection and persistence of parse artifacts."""

    def __init__(
        self,
        storage: BrdStorageService | None = None,
        factory: ParserFactory | None = None,
    ):
        self.storage = storage or BrdStorageService()
        self.factory = factory or ParserFactory()

    def get_parser(self, mime_type: str | None, extension: str) -> DocumentParser:
        return self.factory.get_parser(mime_type, extension)

    async def parse_and_persist(
        self,
        *,
        user_id: int,
        brd_id: int,
        original_path: Path,
        mime_type: str | None,
        extension: str,
    ) -> ParsedDocument:
        parser = self.get_parser(mime_type, extension)
        images_dir = await self.storage.images_dir(user_id, brd_id)
        # A re-parse may extract fewer images than the previous run — clear
        # stale ones first so listings never point at outdated files.
        await self.storage.clear_images_dir(user_id, brd_id)

        # Docling is CPU/IO heavy and synchronous — keep the event loop free.
        parsed = await asyncio.to_thread(
            parser.parse,
            original_path,
            images_dir=images_dir,
        )
        await self.storage.save_parsed_markdown(user_id, brd_id, parsed.text)
        return parsed
