from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.feature_extraction.context import FeatureExtractionContext
from app.ai.feature_extraction.context_builder import FeatureExtractionContextBuilder
from app.ai.feature_extraction.extractor import FeatureExtractor
from app.ai.rag.chunk_retrieval import SimilarChunk
from app.ai.states.feature_state import ExtractedFeatureItem, FeatureExtractionOutput


@pytest.mark.asyncio
async def test_should_use_retrieval_respects_threshold(monkeypatch):
    monkeypatch.setattr(
        "app.ai.feature_extraction.context_builder.settings.RAG_FEATURE_RETRIEVAL_THRESHOLD",
        12,
    )
    builder = FeatureExtractionContextBuilder(MagicMock())
    small = FeatureExtractionContext(
        brd_content="x",
        section_hints="- Auth",
        source="chunks",
        chunk_count=10,
    )
    large = FeatureExtractionContext(
        brd_content="x",
        section_hints="- Auth",
        source="chunks",
        chunk_count=13,
    )
    assert builder.should_use_retrieval(small) is False
    assert builder.should_use_retrieval(large) is True


@pytest.mark.asyncio
async def test_extractor_uses_retrieval_path_for_large_embedded_brds(monkeypatch):
    monkeypatch.setattr(
        "app.ai.feature_extraction.context_builder.settings.RAG_FEATURE_RETRIEVAL_THRESHOLD",
        5,
    )
    monkeypatch.setattr(
        "app.ai.feature_extraction.extractor.settings.RAG_FEATURE_CHUNK_LIMIT",
        4,
    )

    client = MagicMock()
    chunk_repo = MagicMock()
    chunk_repo.list_for_brd = AsyncMock(return_value=[MagicMock()] * 8)
    chunk_repo.count_embedded_for_brd = AsyncMock(return_value=8)

    builder = MagicMock(spec=FeatureExtractionContextBuilder)
    structural = FeatureExtractionContext(
        brd_content="all chunks",
        section_hints="- Auth\n- Billing",
        source="chunks",
        chunk_count=8,
    )
    retrieved_ctx = FeatureExtractionContext(
        brd_content="top-k chunks",
        section_hints="- Auth\n- Billing",
        source="retrieved_chunks",
        chunk_count=8,
    )
    builder.build = AsyncMock(return_value=structural)
    builder.should_use_retrieval = MagicMock(return_value=True)
    builder.should_map_reduce = MagicMock(return_value=False)
    builder.build_from_retrieved = MagicMock(return_value=retrieved_ctx)

    extractor = FeatureExtractor(client, chunk_repo, context_builder=builder)
    expected = FeatureExtractionOutput(
        features=[
            ExtractedFeatureItem(
                title="Auth",
                description="Login",
                confidence=0.9,
                rationale="from retrieved chunks",
            )
        ]
    )

    with (
        patch(
            "app.ai.feature_extraction.extractor.retrieve_similar_chunks",
            new=AsyncMock(
                return_value=[
                    SimilarChunk(
                        id=1,
                        chunk_index=0,
                        section_path="Auth",
                        heading="Auth",
                        chunk_kind="section",
                        content="Users log in",
                        distance=0.1,
                    )
                ]
            ),
        ) as retrieve_mock,
        patch.object(
            extractor,
            "_run_single_pass",
            new=AsyncMock(return_value=expected),
        ) as single_pass,
    ):
        brd = MagicMock()
        brd.id = 7
        brd.name = "Demo BRD"
        result = await extractor.extract(
            brd=brd,
            pipeline_context="",
            operation_id="op-1",
            user_id=1,
        )

    assert result.features[0].title == "Auth"
    retrieve_mock.assert_awaited_once()
    single_pass.assert_awaited_once()
    assert single_pass.await_args.kwargs["context"].source == "retrieved_chunks"
    builder.should_map_reduce.assert_not_called()


@pytest.mark.asyncio
async def test_extractor_falls_back_when_no_embeddings(monkeypatch):
    monkeypatch.setattr(
        "app.ai.feature_extraction.context_builder.settings.RAG_FEATURE_RETRIEVAL_THRESHOLD",
        5,
    )

    client = MagicMock()
    chunk_repo = MagicMock()
    chunks = [MagicMock() for _ in range(8)]
    chunk_repo.list_for_brd = AsyncMock(return_value=chunks)
    chunk_repo.count_embedded_for_brd = AsyncMock(return_value=0)

    builder = MagicMock(spec=FeatureExtractionContextBuilder)
    structural = FeatureExtractionContext(
        brd_content="all chunks",
        section_hints="- Auth",
        source="chunks",
        chunk_count=8,
    )
    builder.build = AsyncMock(return_value=structural)
    builder.should_use_retrieval = MagicMock(return_value=True)
    builder.should_map_reduce = MagicMock(return_value=True)

    extractor = FeatureExtractor(client, chunk_repo, context_builder=builder)
    expected = FeatureExtractionOutput(
        features=[
            ExtractedFeatureItem(
                title="Auth",
                description="Login",
                confidence=0.8,
                rationale="map-reduce",
            )
        ]
    )

    with (
        patch.object(
            extractor,
            "_extract_map_reduce",
            new=AsyncMock(return_value=expected),
        ) as map_reduce,
        patch.object(
            extractor,
            "_refine_draft",
            new=AsyncMock(return_value=expected),
        ) as refine,
    ):
        brd = MagicMock()
        brd.id = 3
        brd.name = "No Embed BRD"
        result = await extractor.extract(
            brd=brd,
            pipeline_context="",
            operation_id="op-2",
            user_id=1,
        )

    assert result.features[0].title == "Auth"
    map_reduce.assert_awaited_once()
    refine.assert_awaited_once()
