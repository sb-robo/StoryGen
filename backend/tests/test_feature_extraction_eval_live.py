"""
Opt-in live eval: runs real feature extraction against the golden BRD and scores it
structurally with evals.score_features. Skipped by default — this calls the real
OpenAI API and costs tokens.

Run explicitly with:
    RUN_LIVE_EVALS=1 uv run pytest backend/tests/test_feature_extraction_eval_live.py -v

Use this to catch prompt-change regressions that unit tests (which mock the LLM) can't see.
"""

import os
from pathlib import Path

import pytest

from app.ai.graphs.feature_extraction import run_feature_extraction_graph
from app.ai.openai_client import OpenAIClient
from app.core.config import settings
from evals.score_features import load_expected, score_feature_list

GOLDEN = Path(__file__).resolve().parents[1] / "evals" / "golden"

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_EVALS") != "1" or not settings.openai_is_configured,
    reason=(
        "Live eval disabled by default. Set RUN_LIVE_EVALS=1 with a configured "
        "OPENAI_API_KEY to run real extraction against the golden BRD."
    ),
)


async def test_live_extraction_scores_against_golden_brd():
    brd_content = (GOLDEN / "sample_brd.md").read_text(encoding="utf-8")
    expected = load_expected(GOLDEN / "sample_features.expected.json")

    client = OpenAIClient()
    output = await run_feature_extraction_graph(
        client,
        brd_name=expected["brd_name"],
        brd_content=brd_content,
        operation_id=None,
        user_id=0,
        brd_id=0,
    )

    features = [f.model_dump() for f in output.features]
    result = score_feature_list(features, expected)

    assert result["passed"], f"Live extraction failed golden checks: {result['checks']}"
