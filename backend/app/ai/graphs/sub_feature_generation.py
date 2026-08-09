from app.ai.graphs.refinement_loop import RefinementLoop
from app.ai.nodes import sub_feature_generation as nodes
from app.ai.openai_client import OpenAIClient
from app.ai.states.sub_feature_state import SubFeatureGenerationOutput


async def run_sub_feature_generation_graph(
    client: OpenAIClient,
    *,
    feature_title: str,
    feature_description: str,
    source_excerpt: str | None,
    clarifying_qa: str,
    brd_context: str = "",
    pipeline_context: str = "",
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    max_iterations: int | None = None,
) -> SubFeatureGenerationOutput:
    """Bounded agentic loop: generate → overlap/completeness critique → revise (if needed)."""
    loop = RefinementLoop[SubFeatureGenerationOutput, object](
        client, max_iterations=max_iterations
    )

    async def generate() -> SubFeatureGenerationOutput:
        return await nodes.generate_sub_features(
            client,
            feature_title=feature_title,
            feature_description=feature_description,
            source_excerpt=source_excerpt,
            clarifying_qa=clarifying_qa,
            brd_context=brd_context,
            pipeline_context=pipeline_context,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=0,
        )

    async def critique(draft: SubFeatureGenerationOutput, iteration: int):
        return await nodes.critique_sub_features(
            client,
            feature_title=feature_title,
            feature_description=feature_description,
            draft=draft,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=iteration,
        )

    async def revise(draft: SubFeatureGenerationOutput, critique_result, iteration: int):
        revised = await nodes.revise_sub_features(
            client,
            feature_title=feature_title,
            feature_description=feature_description,
            draft=draft,
            critique=critique_result,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=iteration,
        )
        return SubFeatureGenerationOutput(sub_features=revised.sub_features)

    return await loop.run(
        generate=generate,
        critique=critique,
        passes=lambda result: result.passes,
        revise=revise,
    )
