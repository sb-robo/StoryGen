from app.ai.nodes import feature_extraction as nodes
from app.ai.openai_client import OpenAIClient
from app.ai.states.feature_state import FeatureExtractionOutput
from app.core.config import settings


async def run_feature_extraction_graph(
    client: OpenAIClient,
    *,
    brd_name: str,
    brd_content: str,
    pipeline_context: str = "",
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    max_iterations: int | None = None,
) -> FeatureExtractionOutput:
    """
    Bounded agentic loop: extract → completeness critique → revise (if needed).
    """
    cap = max_iterations if max_iterations is not None else settings.LLM_MAX_ITERATIONS

    draft = await nodes.generate_features(
        client,
        brd_name=brd_name,
        brd_content=brd_content,
        pipeline_context=pipeline_context,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
        iteration=0,
    )

    for i in range(cap):
        critique = await nodes.critique_completeness(
            client,
            brd_content=brd_content,
            draft=draft,
            pipeline_context=pipeline_context,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=i + 1,
        )
        if critique.passes:
            break

        revised = await nodes.revise_features(
            client,
            brd_content=brd_content,
            draft=draft,
            critique=critique,
            pipeline_context=pipeline_context,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=i + 1,
        )
        draft = FeatureExtractionOutput(features=revised.features)

    return draft
