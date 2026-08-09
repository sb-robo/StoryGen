from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.rag.feature_retrieval import SimilarFeature
from app.ai.rag.story_retrieval import SimilarStory
from app.services.ai._cross_brd import (
    annotate_features_with_cross_brd_matches,
    fetch_cross_brd_feature_context,
    fetch_cross_brd_story_context,
)


@pytest.mark.asyncio
async def test_fetch_cross_brd_feature_context_formats_matches(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(
        "app.services.ai._cross_brd.retrieve_similar_features",
        AsyncMock(
            return_value=[
                SimilarFeature(
                    feature_id=1,
                    brd_id=2,
                    brd_name="Other",
                    title="Billing",
                    summary="Invoices",
                    distance=0.1,
                )
            ]
        ),
    )

    text = await fetch_cross_brd_feature_context(
        MagicMock(),
        client,
        user_id=1,
        exclude_brd_id=9,
        query_parts=["Payments", "billing"],
    )
    assert "Billing" in text
    assert "Other" in text


@pytest.mark.asyncio
async def test_fetch_cross_brd_feature_context_soft_fails(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(
        "app.services.ai._cross_brd.retrieve_similar_features",
        AsyncMock(side_effect=RuntimeError("embed down")),
    )
    text = await fetch_cross_brd_feature_context(
        MagicMock(),
        client,
        user_id=1,
        exclude_brd_id=1,
        query_parts=["x"],
    )
    assert text == ""


@pytest.mark.asyncio
async def test_fetch_cross_brd_story_context_formats_matches(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai._cross_brd.retrieve_similar_stories_cross_brd",
        AsyncMock(
            return_value=[
                SimilarStory(
                    story_id=1,
                    brd_id=2,
                    brd_name="Old",
                    title="Export CSV",
                    story_points=None,
                    summary="Export data",
                    distance=0.2,
                )
            ]
        ),
    )
    text = await fetch_cross_brd_story_context(
        MagicMock(),
        MagicMock(),
        user_id=1,
        exclude_brd_id=3,
        query_parts=["export"],
    )
    assert "Export CSV" in text


@pytest.mark.asyncio
async def test_annotate_features_sets_match_dicts(monkeypatch):
    client = MagicMock()
    client.is_configured = True
    monkeypatch.setattr(
        "app.services.ai._cross_brd.retrieve_similar_features",
        AsyncMock(
            return_value=[
                SimilarFeature(
                    feature_id=8,
                    brd_id=4,
                    brd_name="X",
                    title="Y",
                    summary="Z",
                    distance=0.2,
                )
            ]
        ),
    )
    feature = MagicMock()
    feature.title = "Yish"
    feature.description = "desc"
    feature.cross_brd_similar = None

    await annotate_features_with_cross_brd_matches(
        MagicMock(),
        client,
        user_id=1,
        exclude_brd_id=99,
        features=[feature],
    )
    assert feature.cross_brd_similar[0]["title"] == "Y"
    assert feature.cross_brd_similar[0]["kind"] == "feature"
