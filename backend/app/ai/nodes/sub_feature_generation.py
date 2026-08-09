from app.ai.openai_client import OpenAIClient
from app.ai.prompts import sub_feature_generation as prompts
from app.ai.states.sub_feature_state import (
    SubFeatureCritique,
    SubFeatureGenerationOutput,
    SubFeatureRevisionOutput,
)


async def generate_sub_features(
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
    iteration: int = 0,
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
                    brd_context=brd_context or "(no relevant BRD sections retrieved)",
                    clarifying_qa=clarifying_qa,
                    pipeline_context=pipeline_context or "(no extra settings)",
                ),
            },
        ],
        response_model=SubFeatureGenerationOutput,
        node_name="sub_feature_generate",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
        temperature=0.5,
    )


async def critique_sub_features(
    client: OpenAIClient,
    *,
    feature_title: str,
    feature_description: str,
    draft: SubFeatureGenerationOutput,
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int,
) -> SubFeatureCritique:
    summary_lines = [
        f"- {item.title}: {item.description}" for item in draft.sub_features
    ]
    sub_features_summary = "\n".join(summary_lines) or "(empty)"

    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.CRITIQUE_SYSTEM},
            {
                "role": "user",
                "content": prompts.CRITIQUE_USER.format(
                    feature_title=feature_title,
                    feature_description=feature_description,
                    sub_features_summary=sub_features_summary,
                ),
            },
        ],
        response_model=SubFeatureCritique,
        node_name="sub_feature_critique",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
        temperature=0.2,
    )


async def revise_sub_features(
    client: OpenAIClient,
    *,
    feature_title: str,
    feature_description: str,
    draft: SubFeatureGenerationOutput,
    critique: SubFeatureCritique,
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int,
) -> SubFeatureRevisionOutput:
    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.REVISE_SYSTEM},
            {
                "role": "user",
                "content": prompts.REVISE_USER.format(
                    feature_title=feature_title,
                    feature_description=feature_description,
                    current_sub_features=draft.model_dump_json(),
                    feedback=critique.feedback,
                    issues="\n".join(f"- {i}" for i in critique.issues) or "none",
                ),
            },
        ],
        response_model=SubFeatureRevisionOutput,
        node_name="sub_feature_revise",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
        temperature=0.4,
    )
