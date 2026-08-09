from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.rag.story_retrieval import (
    SimilarStory,
    format_similar_cross_brd_stories,
    format_similar_stories,
    retrieve_similar_stories,
    retrieve_similar_stories_cross_brd,
)
from app.repositories.story_embedding_repository import SimilarEmbeddingRow


def test_format_similar_stories_empty():
    assert "no similar" in format_similar_stories([]).lower()


def test_format_similar_cross_brd_stories_includes_brd():
    formatted = format_similar_cross_brd_stories(
        [
            SimilarStory(
                story_id=5,
                brd_id=2,
                brd_name="Legacy App",
                title="Reset password",
                story_points=3,
                summary="As a user I want to reset password",
                distance=0.15,
            )
        ]
    )
    assert "Legacy App" in formatted
    assert "Reset password" in formatted
    assert "SIMILAR APPROVED STORIES" in formatted


@pytest.mark.asyncio
async def test_retrieve_similar_stories_requires_points(monkeypatch):
    client = MagicMock()
    client.embed_text = AsyncMock(return_value=[0.4, 0.5])
    repo = MagicMock()
    repo.find_similar = AsyncMock(
        return_value=[
            SimilarEmbeddingRow(
                story_id=9,
                brd_id=3,
                brd_name="B",
                title="Login",
                story_points=5,
                text="Login story",
                distance=0.2,
            )
        ]
    )
    monkeypatch.setattr(
        "app.ai.rag.story_retrieval.StoryEmbeddingRepository",
        lambda db: repo,
    )
    monkeypatch.setattr(
        "app.ai.rag.story_retrieval.settings.RAG_SIMILAR_STORY_LIMIT",
        5,
    )

    results = await retrieve_similar_stories(
        MagicMock(),
        client,
        user_id=1,
        title="Sign in",
        description="User signs in",
        acceptance_criteria=["Valid credentials"],
        exclude_story_id=99,
    )

    repo.find_similar.assert_awaited_once_with(
        1,
        [0.4, 0.5],
        limit=5,
        exclude_story_id=99,
        require_points=True,
    )
    assert results[0].story_points == 5


@pytest.mark.asyncio
async def test_retrieve_similar_stories_cross_brd_excludes_brd(monkeypatch):
    client = MagicMock()
    client.embed_text = AsyncMock(return_value=[0.1])
    repo = MagicMock()
    repo.find_similar = AsyncMock(return_value=[])
    monkeypatch.setattr(
        "app.ai.rag.story_retrieval.StoryEmbeddingRepository",
        lambda db: repo,
    )
    monkeypatch.setattr(
        "app.ai.rag.story_retrieval.settings.RAG_CROSS_BRD_STORY_LIMIT",
        3,
    )
    monkeypatch.setattr(
        "app.ai.rag.story_retrieval.settings.RAG_CROSS_BRD_MAX_DISTANCE",
        0.35,
    )

    await retrieve_similar_stories_cross_brd(
        MagicMock(),
        client,
        user_id=2,
        query_text="password reset",
        exclude_brd_id=10,
    )

    repo.find_similar.assert_awaited_once_with(
        2,
        [0.1],
        limit=3,
        exclude_story_id=None,
        exclude_brd_id=10,
        require_points=False,
        max_distance=0.35,
    )
