from pydantic import BaseModel, Field


class BrdChunkResponse(BaseModel):
    id: int
    brd_id: int
    chunk_index: int
    chunk_level: str
    chunk_kind: str
    parent_chunk_index: int | None = None
    heading: str | None = None
    heading_depth: int | None = None
    section_path: str
    content: str
    char_count: int
    has_embedding: bool = Field(description="True when this chunk has a vector embedding")


class BrdChunkListResponse(BaseModel):
    brd_id: int
    chunk_level: str
    total: int
    items: list[BrdChunkResponse]
