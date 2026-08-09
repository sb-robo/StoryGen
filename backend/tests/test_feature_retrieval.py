from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.rag.feature_retrieval import (
    SimilarFeature,
    format_similar_cross_brd_features,
    retrieve_similar_features,
)
from app.repositories.feature_embedding_repository import SimilarFeatureEmbeddingRow


def test_format_similar_cross_brd_features_empty():
    assert "no similar" in format_similar_cross_brd_features([]).lower()


def test_format_similar_cross_brd_features_includes_brd_and_similarity():
    formatted = format_similar_cross_brd_features(
        [
            SimilarFeature(
                feature_id=3,
                brd_id=9,
                brd_name="Payments BRD",
                title="Invoice Export",
                summary="Export invoices as PDF",
                distance=0.2,
            )
        ]
    )
    assert "Payments BRD" in formatted
    assert "Invoice Export" in formatted
    assert "similarity=0.80" in formatted
    assert "SIMILAR APPROVED FEATURES" in formatted


def test_similar_feature_to_match_dict():
    match = SimilarFeature(
        feature_id=1,
        brd_id=2,
        brd_name="A",
        title="T",
        summary="S",
        distance=0.25,
    ).to_match_dict()
    assert match["kind"] == "feature"
    assert match["similarity"] == 0.75


@pytest.mark.asyncio
async def test_retrieve_similar_features_embeds_and_excludes_brd(monkeypatch):
    client = MagicMock()
    client.embed_text = AsyncMock(return_value=[0.1, 0.2])
    repo = MagicMock()
    repo.find_similar = AsyncMock(
        return_value=[
            SimilarFeatureEmbeddingRow(
                feature_id=11,
                brd_id=7,
                brd_name="Other",
                title="Auth",
                text="Login flows",
                distance=0.1,
            )
        ]
    )

    monkeypatch.setattr(
        "app.ai.rag.feature_retrieval.FeatureEmbeddingRepository",
        lambda db: repo,
    )
    monkeypatch.setattr(
        "app.ai.rag.feature_retrieval.settings.RAG_CROSS_BRD_FEATURE_LIMIT",
        4,
    )
    monkeypatch.setattr(
        "app.ai.rag.feature_retrieval.settings.RAG_CROSS_BRD_MAX_DISTANCE",
        0.35,
    )

    results = await retrieve_similar_features(
        MagicMock(),
        client,
        user_id=1,
        query_text="authentication",
        exclude_brd_id=42,
    )

    client.embed_text.assert_awaited_once_with("authentication")
    repo.find_similar.assert_awaited_once_with(
        1,
        [0.1, 0.2],
        limit=4,
        exclude_brd_id=42,
        exclude_feature_id=None,
        max_distance=0.35,
    )
    assert len(results) == 1
    assert results[0].title == "Auth"


@pytest.mark.asyncio
async def test_retrieve_similar_features_empty_query_skips_embed():
    client = MagicMock()
    client.embed_text = AsyncMock()
    results = await retrieve_similar_features(
        MagicMock(),
        client,
        user_id=1,
        query_text="   ",
        exclude_brd_id=1,
    )
    assert results == []
    client.embed_text.assert_not_awaited()
