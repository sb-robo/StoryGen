from app.ai.nodes import story_generation as nodes
from app.ai.openai_client import OpenAIClient
from app.ai.states.story_state import StoryGenerationOutput
from app.core.config import settings


async def run_story_generation_graph(
    client: OpenAIClient,
    *,
    feature_title: str,
    feature_description: str,
    sub_feature_title: str,
    sub_feature_description: str,
    source_excerpt: str | None,
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    max_iterations: int | None = None,
) -> StoryGenerationOutput:
    cap = max_iterations if max_iterations is not None else settings.LLM_MAX_ITERATIONS

    draft = await nodes.generate_stories(
        client,
        feature_title=feature_title,
        feature_description=feature_description,
        sub_feature_title=sub_feature_title,
        sub_feature_description=sub_feature_description,
        source_excerpt=source_excerpt,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
        iteration=0,
    )

    for i in range(cap):
        critique = await nodes.critique_invest(
            client,
            draft=draft,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=i + 1,
        )
        if critique.passes:
            break

        revised = await nodes.revise_stories(
            client,
            sub_feature_title=sub_feature_title,
            sub_feature_description=sub_feature_description,
            draft=draft,
            critique=critique,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=i + 1,
        )
        draft = StoryGenerationOutput(stories=revised.stories)

    return draft
