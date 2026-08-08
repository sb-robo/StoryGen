from app.ai.openai_client import OpenAIClient
from app.ai.prompts import test_case_generation as prompts
from app.ai.states.test_case_state import (
    TestCaseCoverageCritique,
    TestCaseGenerationOutput,
    TestCaseRevisionOutput,
)


async def generate_test_cases(
    client: OpenAIClient,
    *,
    title: str,
    description: str,
    acceptance_criteria: list[str],
    pipeline_context: str = "",
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int = 0,
) -> TestCaseGenerationOutput:
    ac = "\n".join(f"- {c}" for c in acceptance_criteria) or "(none)"
    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.GENERATE_SYSTEM},
            {
                "role": "user",
                "content": prompts.GENERATE_USER.format(
                    title=title,
                    description=description,
                    acceptance_criteria=ac,
                    pipeline_context=pipeline_context or "(no extra settings)",
                ),
            },
        ],
        response_model=TestCaseGenerationOutput,
        node_name="test_case_generate",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )


async def critique_coverage(
    client: OpenAIClient,
    *,
    title: str,
    draft: TestCaseGenerationOutput,
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int,
) -> TestCaseCoverageCritique:
    summary_lines = []
    for tc in draft.test_cases:
        summary_lines.append(f"- [{tc.test_type}] {tc.title}")
    summary = "\n".join(summary_lines) or "(empty)"

    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.CRITIQUE_SYSTEM},
            {
                "role": "user",
                "content": prompts.CRITIQUE_USER.format(
                    title=title,
                    test_cases_summary=summary,
                ),
            },
        ],
        response_model=TestCaseCoverageCritique,
        node_name="test_case_critique",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )


async def revise_test_cases(
    client: OpenAIClient,
    *,
    title: str,
    description: str,
    draft: TestCaseGenerationOutput,
    critique: TestCaseCoverageCritique,
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int,
) -> TestCaseRevisionOutput:
    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.REVISE_SYSTEM},
            {
                "role": "user",
                "content": prompts.REVISE_USER.format(
                    title=title,
                    description=description,
                    current_test_cases=draft.model_dump_json(),
                    feedback=critique.feedback,
                    missing_types=", ".join(critique.missing_types) or "none",
                ),
            },
        ],
        response_model=TestCaseRevisionOutput,
        node_name="test_case_revise",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )
