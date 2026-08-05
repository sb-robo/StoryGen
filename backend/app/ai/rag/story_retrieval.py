from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_client import OpenAIClient
from app.core.config import settings
from app.repositories.story_embedding_repository import StoryEmbeddingRepository


@dataclass
class SimilarStory:
    title: str
    story_points: int
    summary: str
    distance: float


def format_similar_stories(stories: list[SimilarStory]) -> str:
    if not stories:
        return "(no similar approved stories with points — estimate from story scope alone)"
    lines = []
    for item in stories:
        lines.append(
            f"- {item.title} ({item.story_points} pts, similarity={1 - item.distance:.2f}): "
            f"{item.summary[:200]}"
        )
    return "\n".join(lines)


async def retrieve_similar_stories(
    db: AsyncSession,
    client: OpenAIClient,
    *,
    user_id: int,
    title: str,
    description: str,
    acceptance_criteria: list[str],
    exclude_story_id: int | None = None,
) -> list[SimilarStory]:
    ac_text = "\n".join(f"- {c}" for c in acceptance_criteria)
    query_text = f"{title}\n{description}\n{ac_text}".strip()
    embedding = await client.embed_text(query_text)

    repo = StoryEmbeddingRepository(db)
    rows = await repo.find_similar(
        user_id,
        embedding,
        limit=settings.RAG_SIMILAR_STORY_LIMIT,
        exclude_story_id=exclude_story_id,
    )
    return [
        SimilarStory(
            title=row.title,
            story_points=row.story_points,
            summary=row.text,
            distance=row.distance,
        )
        for row in rows
    ]
