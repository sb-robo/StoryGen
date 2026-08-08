import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chunking.factory import ChunkStrategyFactory
from app.ai.chunking.base import ChunkContext
from app.ai.openai_client import OpenAIClient
from app.core.config import settings
from app.db.models.brd_chunk import BrdChunk
from app.db.models.brd_document import BrdDocument
from app.repositories.brd_chunk_repository import BrdChunkRepository
from app.schemas.brd_chunk_schema import BrdChunkListResponse, BrdChunkResponse
from app.schemas.pipeline_settings_schema import BrdChunkStrategy, parse_pipeline_settings

logger = logging.getLogger(__name__)

_EMBED_BATCH_SIZE = 64


class BrdChunkService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        openai_client: OpenAIClient | None = None,
    ):
        self.db = db
        self.repo = BrdChunkRepository(db)
        self.openai_client = openai_client or OpenAIClient(db)
        self.chunk_factory = ChunkStrategyFactory()

    async def index_parsed_markdown(
        self,
        brd: BrdDocument,
        markdown: str,
        *,
        chunk_strategy: BrdChunkStrategy | None = None,
        parser_tables: list | None = None,
    ) -> int:
        """
        Replace stored chunks for a BRD from parsed markdown.

        Embeddings are created when OPENAI_API_KEY is configured; chunks are still
        stored without embeddings when it is not.
        """
        strategy = chunk_strategy or parse_pipeline_settings(brd.pipeline_settings).chunk_level
        embed_batch = None
        if settings.openai_is_configured and self.openai_client.is_configured:
            embed_batch = self._embed_chunks

        context = ChunkContext(
            embed_batch=embed_batch,
            parser_tables=parser_tables,
        )
        drafts = await self.chunk_factory.chunk(
            markdown,
            strategy=strategy,
            context=context,
        )
        await self.repo.delete_for_brd(brd.id)

        if not drafts:
            return 0

        rows: list[BrdChunk] = [
            BrdChunk(
                brd_id=brd.id,
                user_id=brd.user_id,
                chunk_index=draft.chunk_index,
                chunk_level=strategy.value,
                chunk_kind=draft.chunk_kind.value,
                parent_chunk_index=draft.parent_chunk_index,
                heading=draft.heading,
                heading_depth=draft.heading_depth,
                section_path=draft.section_path,
                content=draft.content,
                char_count=draft.char_count,
                embedding=None,
            )
            for draft in drafts
        ]

        if settings.openai_is_configured and self.openai_client.is_configured:
            try:
                embeddings = await self._embed_chunks([row.content for row in rows])
                for row, embedding in zip(rows, embeddings, strict=True):
                    row.embedding = embedding
            except Exception:
                logger.exception(
                    "Failed to embed BRD chunks for brd_id=%s; storing without embeddings",
                    brd.id,
                )

        await self.repo.create_many(rows)
        return len(rows)

    async def _embed_chunks(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _EMBED_BATCH_SIZE):
            batch = texts[start : start + _EMBED_BATCH_SIZE]
            vectors.extend(await self.openai_client.embed_texts(batch))
        return vectors

    async def list_chunks(self, brd: BrdDocument) -> BrdChunkListResponse:
        items = await self.repo.list_for_brd(brd.id)
        chunk_level = (
            items[0].chunk_level
            if items
            else parse_pipeline_settings(brd.pipeline_settings).chunk_level.value
        )
        return BrdChunkListResponse(
            brd_id=brd.id,
            chunk_level=chunk_level,
            total=len(items),
            items=[self._to_response(item) for item in items],
        )

    async def chunk_count(self, brd_id: int) -> int:
        return await self.repo.count_for_brd(brd_id)

    @staticmethod
    def _to_response(item: BrdChunk) -> BrdChunkResponse:
        return BrdChunkResponse(
            id=item.id,
            brd_id=item.brd_id,
            chunk_index=item.chunk_index,
            chunk_level=item.chunk_level,
            chunk_kind=item.chunk_kind,
            parent_chunk_index=item.parent_chunk_index,
            heading=item.heading,
            heading_depth=item.heading_depth,
            section_path=item.section_path,
            content=item.content,
            char_count=item.char_count,
            has_embedding=item.embedding is not None,
        )
