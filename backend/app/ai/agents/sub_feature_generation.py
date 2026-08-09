from app.ai.graphs.sub_feature_generation import run_sub_feature_generation_graph
from app.ai.openai_client import OpenAIClient
from app.ai.states.sub_feature_state import SubFeatureGenerationOutput


async def generate_sub_features_from_feature(
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
) -> SubFeatureGenerationOutput:
    return await run_sub_feature_generation_graph(
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
    )
