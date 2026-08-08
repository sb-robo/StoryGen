from app.ai.graphs.story_generation import run_story_generation_graph
from app.ai.openai_client import OpenAIClient
from app.ai.states.story_state import StoryGenerationOutput


async def generate_stories_from_sub_feature(
    client: OpenAIClient,
    *,
    feature_title: str,
    feature_description: str,
    sub_feature_title: str,
    sub_feature_description: str,
    source_excerpt: str | None,
    pipeline_context: str = "",
    operation_id: str | None,
    user_id: int,
    brd_id: int,
) -> StoryGenerationOutput:
    return await run_story_generation_graph(
        client,
        feature_title=feature_title,
        feature_description=feature_description,
        sub_feature_title=sub_feature_title,
        sub_feature_description=sub_feature_description,
        source_excerpt=source_excerpt,
        pipeline_context=pipeline_context,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )
