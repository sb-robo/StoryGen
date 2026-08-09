from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_client import OpenAIClient
from app.core.config import settings
from app.repositories.feature_embedding_repository import FeatureEmbeddingRepository


@dataclass
class SimilarFeature:
    feature_id: int
    brd_id: int
    brd_name: str
    title: str
    summary: str
    distance: float

    @property
    def similarity(self) -> float:
        return 1 - self.distance

    def to_match_dict(self) -> dict:
        return {
            "kind": "feature",
            "id": self.feature_id,
            "brd_id": self.brd_id,
            "brd_name": self.brd_name,
            "title": self.title,
            "similarity": round(self.similarity, 3),
        }


def format_similar_cross_brd_features(features: list[SimilarFeature]) -> str:
    if not features:
        return "(no similar approved features from your other BRDs)"
    lines = [
        "SIMILAR APPROVED FEATURES FROM YOUR OTHER BRDs "
        "(near-duplicates — do not recreate unless this BRD clearly needs a "
        "distinct capability; prefer merging or narrowing scope):"
    ]
    for item in features:
        summary = item.summary.strip().replace("\n", " ")
        if len(summary) > 180:
            summary = summary[:177] + "..."
        lines.append(
            f"- [BRD: {item.brd_name}] {item.title} "
            f"(similarity={item.similarity:.2f}): {summary or '(no description)'}"
        )
    return "\n".join(lines)


async def retrieve_similar_features(
    db: AsyncSession,
    client: OpenAIClient,
    *,
    user_id: int,
    query_text: str,
    exclude_brd_id: int,
    exclude_feature_id: int | None = None,
    limit: int | None = None,
) -> list[SimilarFeature]:
    text = query_text.strip()
    if not text:
        return []

    embedding = await client.embed_text(text)
    repo = FeatureEmbeddingRepository(db)
    rows = await repo.find_similar(
        user_id,
        embedding,
        limit=limit if limit is not None else settings.RAG_CROSS_BRD_FEATURE_LIMIT,
        exclude_brd_id=exclude_brd_id,
        exclude_feature_id=exclude_feature_id,
        max_distance=settings.RAG_CROSS_BRD_MAX_DISTANCE,
    )
    return [
        SimilarFeature(
            feature_id=row.feature_id,
            brd_id=row.brd_id,
            brd_name=row.brd_name,
            title=row.title,
            summary=row.text,
            distance=row.distance,
        )
        for row in rows
    ]
