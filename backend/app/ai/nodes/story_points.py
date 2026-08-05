from app.ai.openai_client import OpenAIClient
from app.ai.prompts import story_points as prompts
from app.ai.rag.story_retrieval import SimilarStory, format_similar_stories
from app.ai.states.story_points_state import (
    StoryPointsCritique,
    StoryPointsEstimate,
    StoryPointsRevision,
)


async def estimate_points(
    client: OpenAIClient,
    *,
    title: str,
    description: str,
    acceptance_criteria: list[str],
    similar_stories: list[SimilarStory],
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int = 0,
) -> StoryPointsEstimate:
    ac = "\n".join(f"- {c}" for c in acceptance_criteria) or "(none)"
    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.ESTIMATE_SYSTEM},
            {
                "role": "user",
                "content": prompts.ESTIMATE_USER.format(
                    title=title,
                    description=description,
                    acceptance_criteria=ac,
                    similar_stories=format_similar_stories(similar_stories),
                ),
            },
        ],
        response_model=StoryPointsEstimate,
        node_name="story_points_estimate",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )


async def critique_estimate(
    client: OpenAIClient,
    *,
    title: str,
    description: str,
    estimate: StoryPointsEstimate,
    similar_stories: list[SimilarStory],
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int,
) -> StoryPointsCritique:
    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.CRITIQUE_SYSTEM},
            {
                "role": "user",
                "content": prompts.CRITIQUE_USER.format(
                    title=title,
                    description=description,
                    story_points=estimate.story_points,
                    rationale=estimate.rationale,
                    similar_stories=format_similar_stories(similar_stories),
                ),
            },
        ],
        response_model=StoryPointsCritique,
        node_name="story_points_critique",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )


async def revise_estimate(
    client: OpenAIClient,
    *,
    title: str,
    estimate: StoryPointsEstimate,
    critique: StoryPointsCritique,
    operation_id: str | None,
    user_id: int,
    brd_id: int,
    iteration: int,
) -> StoryPointsRevision:
    return await client.parse_structured(
        messages=[
            {"role": "system", "content": prompts.REVISE_SYSTEM},
            {
                "role": "user",
                "content": prompts.REVISE_USER.format(
                    title=title,
                    story_points=estimate.story_points,
                    rationale=estimate.rationale,
                    feedback=critique.feedback,
                    suggested_points=critique.suggested_points or "none",
                ),
            },
        ],
        response_model=StoryPointsRevision,
        node_name="story_points_revise",
        iteration=iteration,
        operation_id=operation_id,
        user_id=user_id,
        brd_id=brd_id,
    )
