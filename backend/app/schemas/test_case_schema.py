from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TestCaseStatusFilter(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class TestCaseResponse(BaseModel):
    id: int
    story_id: int
    user_id: int
    operation_id: str | None = None
    title: str
    steps: str
    expected_result: str
    test_type: str
    confidence: float
    rationale: str
    source_excerpt: str | None = None
    status: str
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestCaseListResponse(BaseModel):
    story_id: int
    items: list[TestCaseResponse]
    total: int

    @classmethod
    def build(
        cls, *, story_id: int, items: list[TestCaseResponse]
    ) -> "TestCaseListResponse":
        return cls(story_id=story_id, items=items, total=len(items))


class TestCaseGenerationResultResponse(BaseModel):
    story_id: int
    operation_id: str
    test_cases: list[TestCaseResponse]
    total: int

    @classmethod
    def build(
        cls,
        *,
        story_id: int,
        operation_id: str,
        test_cases: list[TestCaseResponse],
    ) -> "TestCaseGenerationResultResponse":
        return cls(
            story_id=story_id,
            operation_id=operation_id,
            test_cases=test_cases,
            total=len(test_cases),
        )


class TestCaseUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    steps: str | None = Field(default=None, min_length=1)
    expected_result: str | None = Field(default=None, min_length=1)
    test_type: str | None = Field(default=None, pattern="^(happy_path|edge_case|negative)$")


class TestCaseReviewResponse(BaseModel):
    id: int
    status: str
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
