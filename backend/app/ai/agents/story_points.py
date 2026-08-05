from app.ai.graphs.story_points import run_story_points_graph
from app.ai.openai_client import OpenAIClient
from app.ai.states.story_points_state import StoryPointsEstimate
from sqlalchemy.ext.asyncio import AsyncSession


async def estimate_story_points(
    client: OpenAIClient,
    db: AsyncSession,
    *,
    user_id: int,
    story_id: int,
    brd_id: int,
    title: str,
    description: str,
    acceptance_criteria: list[str],
    operation_id: str | None,
) -> StoryPointsEstimate:
    return await run_story_points_graph(
        client,
        db,
        user_id=user_id,
        story_id=story_id,
        brd_id=brd_id,
        title=title,
        description=description,
        acceptance_criteria=acceptance_criteria,
        operation_id=operation_id,
    )
