from datetime import datetime
from enum import StrEnum
from math import ceil

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class BrdStatusFilter(StrEnum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    PARSE_FAILED = "parse_failed"


class BrdFileExtensionFilter(StrEnum):
    PDF = ".pdf"
    DOCX = ".docx"
    XLSX = ".xlsx"


class BrdSortBy(StrEnum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    NAME = "name"
    FILE_SIZE_BYTES = "file_size_bytes"
    STATUS = "status"
    ORIGINAL_FILENAME = "original_filename"


class BrdSortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


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
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    status: str | None = None
    search: str | None = None
    file_extension: str | None = None
    has_images: bool | None = None
    sort_by: str
    sort_order: str

    @classmethod
    def build(
        cls,
        *,
        items: list[BrdResponse],
        total: int,
        page: int,
        page_size: int,
        status: str | None,
        search: str | None,
        file_extension: str | None,
        has_images: bool | None,
        sort_by: str,
        sort_order: str,
    ) -> "BrdListResponse":
        total_pages = ceil(total / page_size) if page_size else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1 and total > 0,
            status=status,
            search=search,
            file_extension=file_extension,
            has_images=has_images,
            sort_by=sort_by,
            sort_order=sort_order,
        )


class BrdRenameRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
        description="New unique display name for this BRD",
        examples=["Payments Platform BRD v2"],
    )

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class BrdDeleteResponse(BaseModel):
    id: int
    message: str = "BRD deleted successfully"
