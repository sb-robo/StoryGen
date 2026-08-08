from app.ai.nodes import test_case_generation as nodes
from app.ai.openai_client import OpenAIClient
from app.ai.states.test_case_state import TestCaseGenerationOutput
from app.ai.graphs.refinement_loop import RefinementLoop


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
    loop = RefinementLoop[TestCaseGenerationOutput, object](client, max_iterations=max_iterations)

    async def generate() -> TestCaseGenerationOutput:
        return await nodes.generate_test_cases(
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

    async def critique(draft: TestCaseGenerationOutput, iteration: int):
        return await nodes.critique_coverage(
            client,
            title=title,
            draft=draft,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=iteration,
        )

    async def revise(draft: TestCaseGenerationOutput, critique_result, iteration: int):
        revised = await nodes.revise_test_cases(
            client,
            title=title,
            description=description,
            draft=draft,
            critique=critique_result,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=iteration,
        )
        return TestCaseGenerationOutput(test_cases=revised.test_cases)

    return await loop.run(
        generate=generate,
        critique=critique,
        passes=lambda result: result.passes,
        revise=revise,
    )
