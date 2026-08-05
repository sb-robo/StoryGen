"""Unit tests for test case coverage critique loop."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.graphs.test_case_generation import run_test_case_generation_graph
from app.ai.states.test_case_state import (
    ExtractedTestCaseItem,
    TestCaseCoverageCritique,
    TestCaseGenerationOutput,
    TestCaseRevisionOutput,
)


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.parse_structured = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_test_case_graph_stops_when_coverage_passes(mock_client):
    draft = TestCaseGenerationOutput(
        test_cases=[
            ExtractedTestCaseItem(
                title="Happy path login",
                steps="1. Enter valid credentials\n2. Submit",
                expected_result="User is logged in",
                test_type="happy_path",
                confidence=0.9,
                rationale="Core flow",
            )
        ]
    )
    critique_pass = TestCaseCoverageCritique(
        passes=True, missing_types=[], feedback="Adequate for simple story"
    )

    mock_client.parse_structured.side_effect = [draft, critique_pass]

    result = await run_test_case_generation_graph(
        mock_client,
        title="Login",
        description="As a user, I want to log in",
        acceptance_criteria=["Valid credentials work"],
        operation_id="op-1",
        user_id=1,
        brd_id=1,
        max_iterations=2,
    )

    assert len(result.test_cases) == 1
    assert mock_client.parse_structured.call_count == 2


@pytest.mark.asyncio
async def test_test_case_graph_revises_on_coverage_gap(mock_client):
    draft = TestCaseGenerationOutput(
        test_cases=[
            ExtractedTestCaseItem(
                title="Happy path only",
                steps="1. Do thing",
                expected_result="Works",
                test_type="happy_path",
                confidence=0.8,
                rationale="Basic",
            )
        ]
    )
    critique_fail = TestCaseCoverageCritique(
        passes=False,
        missing_types=["negative"],
        feedback="Add invalid input test",
    )
    revised = TestCaseRevisionOutput(
        test_cases=[
            ExtractedTestCaseItem(
                title="Happy path",
                steps="1. Do thing",
                expected_result="Works",
                test_type="happy_path",
                confidence=0.8,
                rationale="Basic",
            ),
            ExtractedTestCaseItem(
                title="Invalid credentials",
                steps="1. Enter bad password",
                expected_result="Error shown",
                test_type="negative",
                confidence=0.85,
                rationale="Error path",
            ),
        ]
    )
    critique_pass = TestCaseCoverageCritique(
        passes=True, missing_types=[], feedback="Good"
    )

    mock_client.parse_structured.side_effect = [
        draft,
        critique_fail,
        revised,
        critique_pass,
    ]

    result = await run_test_case_generation_graph(
        mock_client,
        title="Login",
        description="As a user, I want to log in",
        acceptance_criteria=["Valid credentials work"],
        operation_id="op-1",
        user_id=1,
        brd_id=1,
        max_iterations=2,
    )

    assert len(result.test_cases) == 2
    assert mock_client.parse_structured.call_count == 4
