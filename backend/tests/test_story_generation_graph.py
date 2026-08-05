"""Unit tests for the story generation INVEST critique loop."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.graphs.story_generation import run_story_generation_graph
from app.ai.states.story_state import (
    ExtractedStoryItem,
    StoryGenerationOutput,
    StoryInvestCritique,
    StoryRevisionOutput,
)


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.parse_structured = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_story_graph_stops_when_invest_passes(mock_client):
    draft = StoryGenerationOutput(
        stories=[
            ExtractedStoryItem(
                title="Login",
                description="As a user, I want to log in, so that I can access my account",
                acceptance_criteria=["Valid credentials grant access"],
                confidence=0.9,
                rationale="Core auth flow",
            )
        ]
    )
    critique_pass = StoryInvestCritique(
        passes=True, issues=[], feedback="Meets INVEST"
    )

    mock_client.parse_structured.side_effect = [draft, critique_pass]

    result = await run_story_generation_graph(
        mock_client,
        feature_title="Auth",
        feature_description="Authentication",
        sub_feature_title="Login",
        sub_feature_description="User login",
        source_excerpt=None,
        operation_id="op-1",
        user_id=1,
        brd_id=1,
        max_iterations=2,
    )

    assert len(result.stories) == 1
    assert mock_client.parse_structured.call_count == 2


@pytest.mark.asyncio
async def test_story_graph_revises_on_invest_failure(mock_client):
    draft = StoryGenerationOutput(
        stories=[
            ExtractedStoryItem(
                title="Big story",
                description="As a user, I want everything",
                acceptance_criteria=["TBD"],
                confidence=0.5,
                rationale="Too big",
            )
        ]
    )
    critique_fail = StoryInvestCritique(
        passes=False,
        issues=["Story is not small or testable"],
        feedback="Split into smaller stories",
    )
    revised = StoryRevisionOutput(
        stories=[
            ExtractedStoryItem(
                title="Login",
                description="As a user, I want to log in, so that I can access my account",
                acceptance_criteria=["Valid credentials grant access"],
                confidence=0.9,
                rationale="Scoped",
            ),
            ExtractedStoryItem(
                title="Logout",
                description="As a user, I want to log out, so that I secure my session",
                acceptance_criteria=["Session ends on logout"],
                confidence=0.9,
                rationale="Scoped",
            ),
        ]
    )
    critique_pass = StoryInvestCritique(
        passes=True, issues=[], feedback="Good"
    )

    mock_client.parse_structured.side_effect = [
        draft,
        critique_fail,
        revised,
        critique_pass,
    ]

    result = await run_story_generation_graph(
        mock_client,
        feature_title="Auth",
        feature_description="Authentication",
        sub_feature_title="Session",
        sub_feature_description="Manage sessions",
        source_excerpt=None,
        operation_id="op-1",
        user_id=1,
        brd_id=1,
        max_iterations=2,
    )

    assert len(result.stories) == 2
    assert mock_client.parse_structured.call_count == 4
