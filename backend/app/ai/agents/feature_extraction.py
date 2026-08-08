from app.ai.graphs.feature_extraction import run_feature_extraction_graph
from app.ai.openai_client import OpenAIClient
from app.ai.states.feature_state import FeatureExtractionOutput


async def extract_features_from_brd(
    client: OpenAIClient,
    *,
    brd_name: str,
    brd_content: str,
    pipeline_context: str = "",
    operation_id: str | None,
    user_id: int,
    brd_id: int,
) -> FeatureExtractionOutput:
    return await run_feature_extraction_graph(
        client,
        brd_name=brd_name,
        brd_content=brd_content,
        pipeline_context=pipeline_context,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )
