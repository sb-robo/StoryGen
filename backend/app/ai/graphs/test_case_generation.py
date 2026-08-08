from app.ai.nodes import test_case_generation as nodes
from app.ai.openai_client import OpenAIClient
from app.ai.states.test_case_state import TestCaseGenerationOutput
from app.core.config import settings


async def run_test_case_generation_graph(
    client: OpenAIClient,
    *,
    title: str,
    description: str,
    acceptance_criteria: list[str],
    pipeline_context: str = "",
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    max_iterations: int | None = None,
) -> TestCaseGenerationOutput:
    cap = max_iterations if max_iterations is not None else settings.LLM_MAX_ITERATIONS

    draft = await nodes.generate_test_cases(
        client,
        title=title,
        description=description,
        acceptance_criteria=acceptance_criteria,
        pipeline_context=pipeline_context,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
        iteration=0,
    )

    for i in range(cap):
        critique = await nodes.critique_coverage(
            client,
            title=title,
            draft=draft,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=i + 1,
        )
        if critique.passes:
            break

        revised = await nodes.revise_test_cases(
            client,
            title=title,
            description=description,
            draft=draft,
            critique=critique,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=i + 1,
        )
        draft = TestCaseGenerationOutput(test_cases=revised.test_cases)

    return draft
