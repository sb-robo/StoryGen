from app.ai.nodes import feature_extraction as nodes
from app.ai.openai_client import OpenAIClient
from app.ai.states.feature_state import FeatureExtractionOutput
from app.ai.graphs.refinement_loop import RefinementLoop


async def run_feature_extraction_graph(
    client: OpenAIClient,
    *,
    brd_name: str,
    brd_content: str,
    pipeline_context: str = "",
    existing_constraints: str = "",
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    section_hints: str | None = None,
    max_iterations: int | None = None,
) -> FeatureExtractionOutput:
    """Bounded agentic loop: extract → completeness critique → revise (if needed)."""
    loop = RefinementLoop[FeatureExtractionOutput, object](client, max_iterations=max_iterations)

    async def generate() -> FeatureExtractionOutput:
        return await nodes.generate_features(
            client,
            brd_name=brd_name,
            brd_content=brd_content,
            pipeline_context=pipeline_context,
            existing_constraints=existing_constraints,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=0,
        )

    async def critique(draft: FeatureExtractionOutput, iteration: int):
        return await nodes.critique_completeness(
            client,
            section_hints=section_hints,
            brd_content=brd_content,
            draft=draft,
            pipeline_context=pipeline_context,
            existing_constraints=existing_constraints,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=iteration,
        )

    async def revise(draft: FeatureExtractionOutput, critique_result, iteration: int):
        revised = await nodes.revise_features(
            client,
            brd_content=brd_content,
            draft=draft,
            critique=critique_result,
            pipeline_context=pipeline_context,
            existing_constraints=existing_constraints,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=iteration,
        )
        return FeatureExtractionOutput(features=revised.features)

    return await loop.run(
        generate=generate,
        critique=critique,
        passes=lambda result: result.passes,
        revise=revise,
    )
