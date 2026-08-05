"""Unit tests for the feature extraction agentic loop (no real OpenAI calls)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.graphs.feature_extraction import run_feature_extraction_graph
from app.ai.states.feature_state import (
    ExtractedFeatureItem,
    FeatureCompletenessCritique,
    FeatureExtractionOutput,
    FeatureRevisionOutput,
)


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.parse_structured = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_graph_stops_when_critique_passes(mock_client):
    draft = FeatureExtractionOutput(
        features=[
            ExtractedFeatureItem(
                title="Login",
                description="User authentication",
                confidence=0.9,
                rationale="Required in section 2",
            )
        ]
    )
    critique_pass = FeatureCompletenessCritique(
        passes=True, missing_sections=[], feedback="Looks complete"
    )

    mock_client.parse_structured.side_effect = [draft, critique_pass]

    result = await run_feature_extraction_graph(
        mock_client,
        brd_name="Test BRD",
        brd_content="# Auth\nUsers must log in.",
        operation_id="op-1",
        user_id=1,
        brd_id=1,
        max_iterations=2,
    )

    assert len(result.features) == 1
    assert result.features[0].title == "Login"
    assert mock_client.parse_structured.call_count == 2


@pytest.mark.asyncio
async def test_graph_revises_when_critique_fails(mock_client):
    draft = FeatureExtractionOutput(
        features=[
            ExtractedFeatureItem(
                title="Login",
                description="User authentication",
                confidence=0.9,
                rationale="Required",
            )
        ]
    )
    critique_fail = FeatureCompletenessCritique(
        passes=False,
        missing_sections=["Reporting"],
        feedback="Add reporting feature",
    )
    revised = FeatureRevisionOutput(
        features=[
            ExtractedFeatureItem(
                title="Login",
                description="User authentication",
                confidence=0.9,
                rationale="Required",
            ),
            ExtractedFeatureItem(
                title="Reporting",
                description="Export reports",
                confidence=0.8,
                rationale="Section 5",
            ),
        ]
    )
    critique_pass = FeatureCompletenessCritique(
        passes=True, missing_sections=[], feedback="Complete"
    )

    mock_client.parse_structured.side_effect = [
        draft,
        critique_fail,
        revised,
        critique_pass,
    ]

    result = await run_feature_extraction_graph(
        mock_client,
        brd_name="Test BRD",
        brd_content="# Auth\n# Reporting",
        operation_id="op-1",
        user_id=1,
        brd_id=1,
        max_iterations=2,
    )

    assert len(result.features) == 2
    assert mock_client.parse_structured.call_count == 4
