from app.ai.openai_client import OpenAIClient
from app.ai.prompts import story_generation as prompts
from app.ai.states.story_state import (
    StoryGenerationOutput,
    StoryInvestCritique,
    StoryRevisionOutput,
)


async def generate_stories(
    client: OpenAIClient,
    *,
    feature_title: str,
    feature_description: str,
    sub_feature_title: str,
    sub_feature_description: str,
    source_excerpt: str | None,
    brd_context: str = "",
    pipeline_context: str = "",
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int = 0,
) -> StoryGenerationOutput:
    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.GENERATE_SYSTEM},
            {
                "role": "user",
                "content": prompts.GENERATE_USER.format(
                    feature_title=feature_title,
                    feature_description=feature_description,
                    sub_feature_title=sub_feature_title,
                    sub_feature_description=sub_feature_description,
                    source_excerpt=source_excerpt or "(none)",
                    brd_context=brd_context or "(no relevant BRD sections retrieved)",
                    pipeline_context=pipeline_context or "(no extra settings)",
                ),
            },
        ],
        response_model=StoryGenerationOutput,
        node_name="story_generate",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )


async def critique_invest(
    client: OpenAIClient,
    *,
    draft: StoryGenerationOutput,
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int,
) -> StoryInvestCritique:
    summary_lines = []
    for story in draft.stories:
        ac = "; ".join(story.acceptance_criteria[:3])
        summary_lines.append(
            f"- {story.title}: {story.description[:200]} | AC: {ac}"
        )
    stories_summary = "\n".join(summary_lines) or "(empty)"

    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.CRITIQUE_SYSTEM},
            {
                "role": "user",
                "content": prompts.CRITIQUE_USER.format(stories_summary=stories_summary),
            },
        ],
        response_model=StoryInvestCritique,
        node_name="story_invest_critique",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )


async def revise_stories(
    client: OpenAIClient,
    *,
    sub_feature_title: str,
    sub_feature_description: str,
    draft: StoryGenerationOutput,
    critique: StoryInvestCritique,
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int,
) -> StoryRevisionOutput:
    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.REVISE_SYSTEM},
            {
                "role": "user",
                "content": prompts.REVISE_USER.format(
                    sub_feature_title=sub_feature_title,
                    sub_feature_description=sub_feature_description,
                    current_stories=draft.model_dump_json(),
                    feedback=critique.feedback,
                    issues="\n".join(f"- {i}" for i in critique.issues) or "none",
                ),
            },
        ],
        response_model=StoryRevisionOutput,
        node_name="story_revise",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )
