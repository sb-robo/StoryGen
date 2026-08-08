from datetime import datetime
from enum import StrEnum
from math import ceil

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.utils.operation_urls import operation_result_url, operation_status_url


class OperationStatusValue(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class OperationTypeValue(StrEnum):
    BRD_UPLOAD = "brd_upload"
    BRD_REPARSE = "brd_reparse"
    FEATURE_EXTRACTION = "feature_extraction"
    SUB_FEATURE_GENERATION = "sub_feature_generation"
    STORY_GENERATION = "story_generation"
    STORY_POINT_ESTIMATION = "story_point_estimation"
    TEST_CASE_GENERATION = "test_case_generation"


class OperationSortBy(StrEnum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    COMPLETED_AT = "completed_at"


class OperationSortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class OperationResponse(BaseModel):
    operation_id: str = Field(description="Poll this id for status and result")
    operation_type: str
    status: str
    user_id: int | None = Field(
        default=None,
        description="Owning user id (included on admin list responses)",
    )
    resource_type: str | None = None
    resource_id: int | None = Field(default=None, description="BRD id once the upload row exists")
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def done(self) -> bool:
        return self.status in {
            OperationStatusValue.SUCCEEDED.value,
            OperationStatusValue.FAILED.value,
        }

    @computed_field
    @property
    def status_url(self) -> str:
        return operation_status_url(self.operation_id, self.operation_type)

    @computed_field
    @property
    def result_url(self) -> str:
        return operation_result_url(self.operation_id, self.operation_type)


class OperationResultResponse(BaseModel):
    operation_id: str
    status: str
    resource_type: str | None = None
    resource_id: int | None = None
    result: dict | None = Field(
        default=None,
        description="Type-specific payload when the operation succeeded",
    )


class OperationListResponse(BaseModel):
    items: list[OperationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    status: str | None = None
    operation_type: str | None = None
    resource_type: str | None = None
    resource_id: int | None = None
    user_id: int | None = None
    sort_by: str
    sort_order: str

    @classmethod
    def build(
        cls,
        *,
        items: list[OperationResponse],
        total: int,
        page: int,
        page_size: int,
        status: str | None,
        operation_type: str | None,
        resource_type: str | None,
        resource_id: int | None,
        sort_by: str,
        sort_order: str,
        user_id: int | None = None,
    ) -> "OperationListResponse":
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
            operation_type=operation_type,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            sort_by=sort_by,
            sort_order=sort_order,
        )
