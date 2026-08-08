from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.pipeline_settings_schema import BrdChunkStrategy
from app.services.brd.chunk_service import BrdChunkService


class FakeOpenAIClient:
    is_configured = True

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1536 for _ in texts]


@pytest.mark.asyncio
async def test_index_parsed_markdown_replaces_and_embeds_chunks():
    db = AsyncMock()
    service = BrdChunkService(db, openai_client=FakeOpenAIClient())
    service.repo = AsyncMock()
    service.repo.delete_for_brd = AsyncMock()
    service.repo.create_many = AsyncMock(side_effect=lambda rows: rows)

    brd = MagicMock()
    brd.id = 1
    brd.user_id = 2
    brd.pipeline_settings = {"chunk_level": "section"}
    text = "# Auth\n\nUsers log in.\n\n## Password reset\n\nUsers reset passwords."

    count = await service.index_parsed_markdown(brd, text)

    assert count == 2
    service.repo.delete_for_brd.assert_awaited_once_with(1)
    rows = service.repo.create_many.await_args.args[0]
    assert len(rows) == 2
    assert rows[0].embedding is not None
    assert rows[0].chunk_level == "section"


@pytest.mark.asyncio
async def test_subsection_level_indexes_finer_chunks():
    db = AsyncMock()
    service = BrdChunkService(db, openai_client=FakeOpenAIClient())
    service.repo = AsyncMock()
    service.repo.delete_for_brd = AsyncMock()
    service.repo.create_many = AsyncMock(side_effect=lambda rows: rows)

    brd = MagicMock()
    brd.id = 3
    brd.user_id = 4
    brd.pipeline_settings = {}
    text = (
        "# Platform\n\nOverview.\n\n"
        "## Authentication\n\nLogin details.\n\n"
        "### MFA\n\nSecond factor.\n"
    )

    count = await service.index_parsed_markdown(
        brd, text, chunk_strategy=BrdChunkStrategy.SUBSECTION
    )

    assert count == 3
    rows = service.repo.create_many.await_args.args[0]
    assert rows[-1].section_path.endswith("MFA")
