from app.ai.nodes import story_points as nodes
from app.ai.openai_client import OpenAIClient
from app.ai.rag.story_retrieval import retrieve_similar_stories
from app.ai.states.story_points_state import StoryPointsEstimate
from app.ai.graphs.refinement_loop import RefinementLoop
from sqlalchemy.ext.asyncio import AsyncSession


async def run_story_points_graph(
    client: OpenAIClient,
    db: AsyncSession,
    *,
    user_id: int,
    story_id: int,
    brd_id: int,
    title: str,
    description: str,
    acceptance_criteria: list[str],
    pipeline_context: str = "",
    operation_id: str | None,
    max_iterations: int | None = None,
) -> StoryPointsEstimate:
    similar = await retrieve_similar_stories(
        db,
        client,
        user_id=user_id,
        title=title,
        description=description,
        acceptance_criteria=acceptance_criteria,
        exclude_story_id=story_id,
    )

    loop = RefinementLoop[StoryPointsEstimate, object](client, max_iterations=max_iterations)

    async def generate() -> StoryPointsEstimate:
        return await nodes.estimate_points(
            client,
            title=title,
            description=description,
            acceptance_criteria=acceptance_criteria,
            similar_stories=similar,
            pipeline_context=pipeline_context,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=0,
        )

    async def critique(estimate: StoryPointsEstimate, iteration: int):
        return await nodes.critique_estimate(
            client,
            title=title,
            description=description,
            estimate=estimate,
            similar_stories=similar,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=iteration,
        )

    async def revise(estimate: StoryPointsEstimate, critique_result, iteration: int):
        revised = await nodes.revise_estimate(
            client,
            title=title,
            estimate=estimate,
            critique=critique_result,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
            iteration=iteration,
        )
        return StoryPointsEstimate(
            story_points=revised.story_points,
            rationale=revised.rationale,
            confidence=revised.confidence,
        )

    return await loop.run(
        generate=generate,
        critique=critique,
        passes=lambda result: result.passes,
        revise=revise,
    )
