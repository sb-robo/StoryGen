from dataclasses import dataclass

from app.ai.openai_client import OpenAIClient
from app.core.config import settings
from app.repositories.brd_chunk_repository import BrdChunkRepository, SimilarChunkRow


@dataclass
class SimilarChunk:
    id: int
    chunk_index: int
    section_path: str
    heading: str | None
    chunk_kind: str
    content: str
    distance: float

    @classmethod
    def from_row(cls, row: SimilarChunkRow) -> "SimilarChunk":
        return cls(
            id=row.id,
            chunk_index=row.chunk_index,
            section_path=row.section_path,
            heading=row.heading,
            chunk_kind=row.chunk_kind,
            content=row.content,
            distance=row.distance,
        )


FEATURE_RETRIEVAL_QUERY = (
    "Product features, capabilities, functional requirements, and user-facing "
    "behaviors described in this business requirements document."
)


def format_similar_chunks(
    chunks: list[SimilarChunk],
    *,
    empty_message: str = "(no relevant BRD sections retrieved)",
    max_chars_per_chunk: int = 1500,
) -> str:
    if not chunks:
        return empty_message
    parts: list[str] = []
    for item in chunks:
        header = f"### [{item.section_path}]"
        if item.heading:
            header += f" — {item.heading}"
        if item.chunk_kind != "section":
            header += f" ({item.chunk_kind})"
        similarity = 1 - item.distance
        header += f" [similarity={similarity:.2f}]"
        body = item.content.strip()
        if len(body) > max_chars_per_chunk:
            body = body[: max_chars_per_chunk - 3] + "..."
        parts.append(f"{header}\n{body}")
    return "\n\n".join(parts)


def build_retrieval_query(*parts: str | None) -> str:
    cleaned = [p.strip() for p in parts if p and p.strip()]
    return "\n".join(cleaned).strip()


async def retrieve_similar_chunks(
    client: OpenAIClient,
    chunk_repo: BrdChunkRepository,
    *,
    brd_id: int,
    query_text: str,
    limit: int | None = None,
) -> list[SimilarChunk]:
    """Embed query_text and return top-k similar chunks for the BRD."""
    text = query_text.strip()
    if not text:
        return []

    embedding = await client.embed_text(text)
    rows = await chunk_repo.find_similar(
        brd_id,
        embedding,
        limit=limit if limit is not None else settings.RAG_SIMILAR_CHUNK_LIMIT,
    )
    return [SimilarChunk.from_row(row) for row in rows]
