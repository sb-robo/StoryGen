from app.ai.graphs.test_case_generation import run_test_case_generation_graph
from app.ai.openai_client import OpenAIClient
from app.ai.states.test_case_state import TestCaseGenerationOutput


async def generate_test_cases_for_story(
    client: OpenAIClient,
    *,
    title: str,
    description: str,
    acceptance_criteria: list[str],
    operation_id: str | None,
    user_id: int,
    brd_id: int,
) -> TestCaseGenerationOutput:
    return await run_test_case_generation_graph(
        client,
        title=title,
        description=description,
        acceptance_criteria=acceptance_criteria,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )
