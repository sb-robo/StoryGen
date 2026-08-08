from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

from app.ai.openai_client import OpenAIClient
from app.core.config import settings
from app.utils.process_tracker import track

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
    ) -> TDraft:
        draft = await generate()

        for iteration in range(1, self.max_iterations + 1):
            critique_result = await critique(draft, iteration)
            if passes(critique_result):
                track("critique passed", round=iteration)
                break
            track("critique failed; revising", round=iteration)
            draft = await revise(draft, critique_result, iteration)

        return draft
