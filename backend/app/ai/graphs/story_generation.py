from app.ai.nodes import story_generation as nodes
from app.ai.openai_client import OpenAIClient
from app.ai.states.story_state import StoryGenerationOutput
from app.ai.graphs.refinement_loop import RefinementLoop


async def run_story_generation_graph(
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
    max_iterations: int | None = None,
) -> StoryGenerationOutput:
    loop = RefinementLoop[StoryGenerationOutput, object](client, max_iterations=max_iterations)

    async def generate() -> StoryGenerationOutput:
        return await nodes.generate_stories(
            client,
            feature_title=feature_title,
            feature_description=feature_description,
            sub_feature_title=sub_feature_title,
            sub_feature_description=sub_feature_description,
            source_excerpt=source_excerpt,
            brd_context=brd_context,
            pipeline_context=pipeline_context,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=0,
        )

    async def critique(draft: StoryGenerationOutput, iteration: int):
        return await nodes.critique_invest(
            client,
            draft=draft,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=iteration,
        )

    async def revise(draft: StoryGenerationOutput, critique_result, iteration: int):
        revised = await nodes.revise_stories(
            client,
            sub_feature_title=sub_feature_title,
            sub_feature_description=sub_feature_description,
            draft=draft,
            critique=critique_result,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=iteration,
        )
        return StoryGenerationOutput(stories=revised.stories)

    return await loop.run(
        generate=generate,
        critique=critique,
        passes=lambda result: result.passes,
        revise=revise,
    )
