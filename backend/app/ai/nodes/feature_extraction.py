import re

from app.ai.openai_client import OpenAIClient
from app.ai.prompts import feature_extraction as prompts
from app.ai.states.feature_state import (
    FeatureCompletenessCritique,
    FeatureExtractionOutput,
    FeatureRevisionOutput,
)


def extract_section_hints(brd_content: str, *, max_lines: int = 40) -> str:
    """Pull markdown headings as cheap structure hints for the critique node."""
    headings: list[str] = []
    for line in brd_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            headings.append(stripped.lstrip("#").strip())
        elif re.match(r"^\d+(\.\d+)*\s+\S", stripped):
            headings.append(stripped)
        if len(headings) >= max_lines:
            break
    return "\n".join(headings) if headings else "(no clear headings found)"


async def generate_features(
    client: OpenAIClient,
    *,
    brd_name: str,
    brd_content: str,
    pipeline_context: str = "",
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int = 0,
) -> FeatureExtractionOutput:
    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.EXTRACT_SYSTEM},
            {
                "role": "user",
                "content": prompts.EXTRACT_USER.format(
                    brd_name=brd_name,
                    brd_content=brd_content,
                    pipeline_context=pipeline_context or "(no extra settings)",
                ),
            },
        ],
        response_model=FeatureExtractionOutput,
        node_name="feature_extract",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )


async def critique_completeness(
    client: OpenAIClient,
    *,
    draft: FeatureExtractionOutput,
    pipeline_context: str = "",
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int,
    section_hints: str | None = None,
    brd_content: str | None = None,
) -> FeatureCompletenessCritique:
    hints = section_hints
    if hints is None:
        hints = extract_section_hints(brd_content or "")
    feature_titles = "\n".join(f"- {f.title}" for f in draft.features) or "(empty)"
    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.CRITIQUE_SYSTEM},
            {
                "role": "user",
                "content": prompts.CRITIQUE_USER.format(
                    section_hints=hints,
                    feature_titles=feature_titles,
                    pipeline_context=pipeline_context or "(no extra settings)",
                ),
            },
        ],
        response_model=FeatureCompletenessCritique,
        node_name="feature_critique",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )


async def revise_features(
    client: OpenAIClient,
    *,
    brd_content: str,
    draft: FeatureExtractionOutput,
    critique: FeatureCompletenessCritique,
    pipeline_context: str = "",
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int,
) -> FeatureRevisionOutput:
    excerpt = brd_content[:12000]
    current = draft.model_dump_json()
    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.REVISE_SYSTEM},
            {
                "role": "user",
                "content": prompts.REVISE_USER.format(
                    brd_excerpt=excerpt,
                    current_features=current,
                    feedback=critique.feedback,
                    missing_sections=", ".join(critique.missing_sections) or "none",
                    pipeline_context=pipeline_context or "(no extra settings)",
                ),
            },
        ],
        response_model=FeatureRevisionOutput,
        node_name="feature_revise",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )
