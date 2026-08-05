from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field


class BrdStatusFilter(StrEnum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    PARSE_FAILED = "parse_failed"


class BrdResponse(BaseModel):
    id: int
    user_id: int
    name: str = Field(description="Display name for this BRD")
    original_filename: str
    mime_type: str | None
    file_extension: str
    file_size_bytes: int
    status: str
    error_message: str | None = None
    page_count: int | None = None
    table_count: int = 0
    image_count: int = 0
    created_at: datetime
    updated_at: datetime
    preview: str | None = Field(
        default=None,
        description="Short preview of parsed Markdown (list views)",
    )

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def file_size_mb(self) -> float:
        return round(self.file_size_bytes / (1024 * 1024), 3)

    @computed_field
    @property
    def is_ready(self) -> bool:
        return self.status == BrdStatusFilter.PARSED.value

    @computed_field
    @property
    def has_parse_error(self) -> bool:
        return self.status == BrdStatusFilter.PARSE_FAILED.value


class BrdImageResponse(BaseModel):
    filename: str
    size_bytes: int
    content_type: str
    url: str = Field(description="Relative API path to fetch this image")


class BrdDetailResponse(BrdResponse):
    images: list[BrdImageResponse] = Field(default_factory=list)
    parsed_text: str | None = Field(
        default=None,
        description="Full Markdown extracted from the BRD (omit with include_text=false)",
    )
    char_count: int | None = None
    word_count: int | None = None


class BrdContentResponse(BaseModel):
    brd_id: int
    status: str
    original_filename: str
    content_type: str = "text/markdown"
    char_count: int
    word_count: int
    content: str


class BrdImageListResponse(BaseModel):
    brd_id: int
    total: int
    items: list[BrdImageResponse]


class BrdListResponse(BaseModel):
    items: list[BrdResponse]
    total: int
    skip: int
    limit: int
    status: str | None = None
    search: str | None = None


class BrdDeleteResponse(BaseModel):
    id: int
    message: str = "BRD deleted successfully"
