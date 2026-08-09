from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

from app.ai.openai_client import OpenAIClient
from app.core.config import settings
from app.utils.process_tracker import track, track_error

TDraft = TypeVar("TDraft")
TCritique = TypeVar("TCritique")


class RefinementLoop(Generic[TDraft, TCritique]):
    """
    Template for bounded generate → critique → revise agentic loops.

    Used by feature extraction, story generation, story points, and test cases.
    """

    def __init__(
        self,
        client: OpenAIClient,
        *,
        max_iterations: int | None = None,
    ):
        self.client = client
        self.max_iterations = (
            max_iterations if max_iterations is not None else settings.LLM_MAX_ITERATIONS
        )

    async def run(
        self,
        *,
        generate: Callable[[], Awaitable[TDraft]],
        critique: Callable[[TDraft, int], Awaitable[TCritique]],
        passes: Callable[[TCritique], bool],
        revise: Callable[[TDraft, TCritique, int], Awaitable[TDraft]],
        on_unresolved: Callable[[TDraft, TCritique], None] | None = None,
    ) -> TDraft:
        draft = await generate()

        for iteration in range(1, self.max_iterations + 1):
            critique_result = await critique(draft, iteration)
            if passes(critique_result):
                track("critique passed", round=iteration)
                return draft
            track("critique failed; revising", round=iteration)
            draft = await revise(draft, critique_result, iteration)

        # The last revision was never re-checked above — verify it before returning
        # instead of silently shipping an unverified draft once iterations run out.
        final_round = self.max_iterations + 1
        final_critique = await critique(draft, final_round)
        if passes(final_critique):
            track("critique passed on final check", round=final_round)
        else:
            track_error(
                "refinement loop exhausted iterations without a passing critique",
                round=final_round,
            )
            if on_unresolved is not None:
                on_unresolved(draft, final_critique)

        return draft
