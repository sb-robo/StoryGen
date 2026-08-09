"""Unit tests for RefinementLoop's exhausted-iterations final check."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.graphs.refinement_loop import RefinementLoop


@pytest.mark.asyncio
async def test_loop_returns_immediately_once_passing():
    client = MagicMock()
    loop = RefinementLoop[str, dict](client, max_iterations=2)

    generate = AsyncMock(return_value="draft-0")
    critique = AsyncMock(return_value={"passes": True})
    revise = AsyncMock()

    result = await loop.run(
        generate=generate,
        critique=critique,
        passes=lambda c: c["passes"],
        revise=revise,
    )

    assert result == "draft-0"
    critique.assert_awaited_once()
    revise.assert_not_awaited()


@pytest.mark.asyncio
async def test_loop_does_final_critique_when_iterations_exhausted():
    client = MagicMock()
    loop = RefinementLoop[str, dict](client, max_iterations=2)

    generate = AsyncMock(return_value="draft-0")
    # Never passes, across every critique call including the final check.
    critique = AsyncMock(return_value={"passes": False})
    revise = AsyncMock(side_effect=["draft-1", "draft-2"])
    on_unresolved = MagicMock()

    result = await loop.run(
        generate=generate,
        critique=critique,
        passes=lambda c: c["passes"],
        revise=revise,
        on_unresolved=on_unresolved,
    )

    assert result == "draft-2"
    # 2 critiques inside the loop (iterations 1, 2) + 1 final re-check = 3.
    assert critique.await_count == 3
    assert revise.await_count == 2
    on_unresolved.assert_called_once_with("draft-2", {"passes": False})


@pytest.mark.asyncio
async def test_loop_final_critique_can_still_pass():
    client = MagicMock()
    loop = RefinementLoop[str, dict](client, max_iterations=1)

    generate = AsyncMock(return_value="draft-0")
    critique = AsyncMock(
        side_effect=[{"passes": False}, {"passes": True}],
    )
    revise = AsyncMock(return_value="draft-1")
    on_unresolved = MagicMock()

    result = await loop.run(
        generate=generate,
        critique=critique,
        passes=lambda c: c["passes"],
        revise=revise,
        on_unresolved=on_unresolved,
    )

    assert result == "draft-1"
    assert critique.await_count == 2
    on_unresolved.assert_not_called()
