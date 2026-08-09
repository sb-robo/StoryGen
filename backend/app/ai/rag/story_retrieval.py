from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_client import OpenAIClient
from app.core.config import settings
from app.repositories.story_embedding_repository import StoryEmbeddingRepository


@dataclass
class SimilarStory:
    story_id: int | None
    brd_id: int | None
    brd_name: str | None
    title: str
    story_points: int | None
    summary: str
    distance: float

    @property
    def similarity(self) -> float:
        return 1 - self.distance

    def to_match_dict(self) -> dict:
        return {
            "kind": "story",
            "id": self.story_id,
            "brd_id": self.brd_id,
            "brd_name": self.brd_name or "(unknown BRD)",
            "title": self.title,
            "similarity": round(self.similarity, 3),
        }


def format_similar_stories(stories: list[SimilarStory]) -> str:
    if not stories:
        return "(no similar approved stories with points — estimate from story scope alone)"
    lines = []
    for item in stories:
        pts = f"{item.story_points} pts" if item.story_points is not None else "unpointed"
        lines.append(
            f"- {item.title} ({pts}, similarity={item.similarity:.2f}): "
            f"{item.summary[:200]}"
        )
    return "\n".join(lines)


def format_similar_cross_brd_stories(stories: list[SimilarStory]) -> str:
    if not stories:
        return "(no similar approved stories from your other BRDs)"
    lines = [
        "SIMILAR APPROVED STORIES FROM YOUR OTHER BRDs "
        "(near-duplicates — avoid recreating the same user outcome unless this "
        "sub-feature clearly needs a distinct story; prefer reuse of intent):"
    ]
    for item in stories:
        brd = item.brd_name or "(unknown BRD)"
        summary = item.summary.strip().replace("\n", " ")
        if len(summary) > 180:
            summary = summary[:177] + "..."
        lines.append(
            f"- [BRD: {brd}] {item.title} "
            f"(similarity={item.similarity:.2f}): {summary or '(no description)'}"
        )
    return "\n".join(lines)


def _story_query_text(
    title: str,
    description: str,
    acceptance_criteria: list[str] | None = None,
) -> str:
    parts = [title, description]
    if acceptance_criteria:
        parts.append("\n".join(f"- {c}" for c in acceptance_criteria))
    return "\n".join(p for p in parts if p and str(p).strip()).strip()


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
    """Retrieve similar stories for story-point calibration (requires approved points)."""
    query_text = _story_query_text(title, description, acceptance_criteria)
    embedding = await client.embed_text(query_text)

    repo = StoryEmbeddingRepository(db)
    rows = await repo.find_similar(
        user_id,
        embedding,
        limit=settings.RAG_SIMILAR_STORY_LIMIT,
        exclude_story_id=exclude_story_id,
        require_points=True,
    )
    return [
        SimilarStory(
            story_id=row.story_id,
            brd_id=row.brd_id,
            brd_name=row.brd_name,
            title=row.title,
            story_points=row.story_points,
            summary=row.text,
            distance=row.distance,
        )
        for row in rows
    ]


async def retrieve_similar_stories_cross_brd(
    db: AsyncSession,
    client: OpenAIClient,
    *,
    user_id: int,
    query_text: str,
    exclude_brd_id: int,
    exclude_story_id: int | None = None,
    limit: int | None = None,
) -> list[SimilarStory]:
    """Retrieve similar approved stories from the user's other BRDs (dedup)."""
    text = query_text.strip()
    if not text:
        return []

    embedding = await client.embed_text(text)
    repo = StoryEmbeddingRepository(db)
    rows = await repo.find_similar(
        user_id,
        embedding,
        limit=limit if limit is not None else settings.RAG_CROSS_BRD_STORY_LIMIT,
        exclude_story_id=exclude_story_id,
        exclude_brd_id=exclude_brd_id,
        require_points=False,
        max_distance=settings.RAG_CROSS_BRD_MAX_DISTANCE,
    )
    return [
        SimilarStory(
            story_id=row.story_id,
            brd_id=row.brd_id,
            brd_name=row.brd_name,
            title=row.title,
            story_points=row.story_points,
            summary=row.text,
            distance=row.distance,
        )
        for row in rows
    ]
