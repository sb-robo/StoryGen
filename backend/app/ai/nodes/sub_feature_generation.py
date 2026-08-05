from app.ai.openai_client import OpenAIClient
from app.ai.prompts import sub_feature_generation as prompts
from app.ai.states.sub_feature_state import SubFeatureGenerationOutput


async def generate_sub_features(
    client: OpenAIClient,
    *,
    feature_title: str,
    feature_description: str,
    source_excerpt: str | None,
    operation_id: str | None,
    user_id: int,
    brd_id: int,
) -> SubFeatureGenerationOutput:
    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.GENERATE_SYSTEM},
            {
                "role": "user",
                "content": prompts.GENERATE_USER.format(
                    feature_title=feature_title,
                    feature_description=feature_description,
                    source_excerpt=source_excerpt or "(none)",
                ),
            },
        ],
        response_model=SubFeatureGenerationOutput,
        node_name="sub_feature_generate",
        iteration=0,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )
