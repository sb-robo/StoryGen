"""Unit tests for the sub-feature overlap/completeness critique loop."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.graphs.sub_feature_generation import run_sub_feature_generation_graph
from app.ai.states.sub_feature_state import (
    ExtractedSubFeatureItem,
    SubFeatureCritique,
    SubFeatureGenerationOutput,
    SubFeatureRevisionOutput,
)


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.parse_structured = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_sub_feature_graph_stops_when_critique_passes(mock_client):
    draft = SubFeatureGenerationOutput(
        sub_features=[
            ExtractedSubFeatureItem(
                title="Email login",
                description="Sign in with email and password",
                confidence=0.9,
                rationale="Core auth slice",
            )
        ]
    )
    critique_pass = SubFeatureCritique(passes=True, issues=[], feedback="Well scoped")

    mock_client.parse_structured.side_effect = [draft, critique_pass]

    result = await run_sub_feature_generation_graph(
        mock_client,
        feature_title="Authentication",
        feature_description="Users can sign in",
        source_excerpt=None,
        clarifying_qa="(none)",
        operation_id="op-1",
        user_id=1,
        brd_id=1,
        max_iterations=2,
    )

    assert len(result.sub_features) == 1
    assert mock_client.parse_structured.call_count == 2


@pytest.mark.asyncio
async def test_sub_feature_graph_revises_on_overlap(mock_client):
    draft = SubFeatureGenerationOutput(
        sub_features=[
            ExtractedSubFeatureItem(
                title="Login",
                description="Sign in",
                confidence=0.8,
                rationale="Auth",
            ),
            ExtractedSubFeatureItem(
                title="Sign in flow",
                description="Sign in with credentials",
                confidence=0.8,
                rationale="Auth",
            ),
        ]
    )
    critique_fail = SubFeatureCritique(
        passes=False,
        issues=["Login and Sign in flow overlap"],
        feedback="Merge the overlapping sub-features",
    )
    revised = SubFeatureRevisionOutput(
        sub_features=[
            ExtractedSubFeatureItem(
                title="Email login",
                description="Sign in with email and password",
                confidence=0.9,
                rationale="Auth",
            ),
            ExtractedSubFeatureItem(
                title="Password reset",
                description="Reset a forgotten password via email",
                confidence=0.85,
                rationale="Auth",
            ),
        ]
    )
    critique_pass = SubFeatureCritique(passes=True, issues=[], feedback="Good")

    mock_client.parse_structured.side_effect = [
        draft,
        critique_fail,
        revised,
        critique_pass,
    ]

    result = await run_sub_feature_generation_graph(
        mock_client,
        feature_title="Authentication",
        feature_description="Users can sign in",
        source_excerpt=None,
        clarifying_qa="(none)",
        operation_id="op-1",
        user_id=1,
        brd_id=1,
        max_iterations=2,
    )

    assert len(result.sub_features) == 2
    assert result.sub_features[0].title == "Email login"
    assert mock_client.parse_structured.call_count == 4
