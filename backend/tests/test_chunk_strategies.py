import pytest

from app.ai.chunking.base import ChunkContext
from app.ai.chunking.factory import ChunkStrategyFactory
from app.ai.chunking.strategies.fixed_size_strategy import FixedSizeChunkStrategy
from app.ai.chunking.strategies.hybrid_strategy import HybridChunkStrategy
from app.ai.chunking.strategies.requirement_strategy import RequirementChunkStrategy
from app.ai.chunking.table_extractor import TableExtractor
from app.ai.chunking.types import ChunkKind
from app.schemas.pipeline_settings_schema import BrdChunkStrategy, CHUNK_STRATEGY_GUIDE


def test_requirement_strategy_splits_numbered_items():
    strategy = RequirementChunkStrategy()
    text = (
        "Preamble line.\n\n"
        "1.1 User login\nThe system shall authenticate users.\n\n"
        "1.2 Password reset\nUsers must reset via email.\n\n"
        "REQ-42 Audit trail\nAll actions shall be logged."
    )
    chunks = strategy.build_chunks(text)
    assert len(chunks) >= 3
    assert all(chunk.chunk_kind == ChunkKind.REQUIREMENT for chunk in chunks)
    assert any("1.1" in (chunk.heading or "") for chunk in chunks)
    assert any("REQ-42" in (chunk.heading or "") for chunk in chunks)


def test_fixed_size_strategy_produces_multiple_windows():
    strategy = FixedSizeChunkStrategy()
    text = "Word " * 800
    chunks = strategy.build_chunks(text, context=ChunkContext(max_chunk_chars=500))
    assert len(chunks) >= 2
    assert all(chunk.chunk_kind == ChunkKind.FIXED_WINDOW for chunk in chunks)
    assert all(chunk.char_count <= 500 for chunk in chunks)


def test_table_extractor_finds_markdown_table():
    extractor = TableExtractor()
    text = "# Spec\n\nIntro.\n\n| Col A | Col B |\n| --- | --- |\n| a | b |\n\nAfter table."
    prose, tables = extractor.extract_from_markdown(text)
    assert len(tables) == 1
    assert "| Col A |" in tables[0]
    assert "| Col A |" not in prose


def test_all_strategies_have_guide_metadata():
    for strategy in BrdChunkStrategy:
        meta = CHUNK_STRATEGY_GUIDE[strategy]
        assert meta["label"]
        assert meta["when_to_use"]
        assert meta["tradeoffs"]


@pytest.mark.asyncio
async def test_hybrid_strategy_creates_table_child_chunks():
    strategy = HybridChunkStrategy()
    text = (
        "# Payments\n\nOverview paragraph.\n\n"
        "| Rule | Value |\n| --- | --- |\n| Max | 100 |\n\n"
        "Tail paragraph."
    )

    async def fake_embed(texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] * 768 for _ in texts]

    from app.ai.chunking.base import ChunkContext

    chunks = await strategy.chunk(text, context=ChunkContext(embed_batch=fake_embed))
    kinds = {chunk.chunk_kind for chunk in chunks}
    assert ChunkKind.SECTION in kinds
    assert ChunkKind.TABLE in kinds
    table_chunks = [c for c in chunks if c.chunk_kind == ChunkKind.TABLE]
    assert table_chunks[0].parent_chunk_index is not None


def test_chunk_strategy_factory_returns_all_strategies():
    factory = ChunkStrategyFactory()
    for strategy in BrdChunkStrategy:
        assert factory.get(strategy).strategy == strategy
