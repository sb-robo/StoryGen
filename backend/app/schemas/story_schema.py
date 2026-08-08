from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StoryStatusFilter(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class StoryResponse(BaseModel):
    id: int
    sub_feature_id: int
    user_id: int
    operation_id: str | None = None
    title: str
    description: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    confidence: float
    rationale: str
    source_excerpt: str | None = None
    source_chunk_id: int | None = None
    status: str
    story_points: int | None = None
    points_rationale: str | None = None
    points_status: str | None = None
    points_reviewed_by: int | None = None
    points_reviewed_at: datetime | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoryListResponse(BaseModel):
    sub_feature_id: int
    items: list[StoryResponse]
    total: int

    @classmethod
    def build(
        cls, *, sub_feature_id: int, items: list[StoryResponse]
    ) -> "StoryListResponse":
        return cls(sub_feature_id=sub_feature_id, items=items, total=len(items))


class StoryGenerationResultResponse(BaseModel):
    sub_feature_id: int
    operation_id: str
    stories: list[StoryResponse]
    total: int

    @classmethod
    def build(
        cls,
        *,
        sub_feature_id: int,
        operation_id: str,
        stories: list[StoryResponse],
    ) -> "StoryGenerationResultResponse":
        return cls(
            sub_feature_id=sub_feature_id,
            operation_id=operation_id,
            stories=stories,
            total=len(stories),
        )


class StoryUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = Field(default=None, min_length=1)
    acceptance_criteria: list[str] | None = None


class StoryReviewResponse(BaseModel):
    id: int
    status: str
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None


class StoryPointsUpdateRequest(BaseModel):
    story_points: int = Field(ge=1, le=21)
    points_rationale: str | None = Field(default=None, min_length=1)


class StoryPointsResultResponse(BaseModel):
    story_id: int
    operation_id: str
    story_points: int
    points_rationale: str
    points_status: str

    @classmethod
    def build(
        cls,
        *,
        story_id: int,
        operation_id: str,
        story_points: int,
        points_rationale: str,
        points_status: str,
    ) -> "StoryPointsResultResponse":
        return cls(
            story_id=story_id,
            operation_id=operation_id,
            story_points=story_points,
            points_rationale=points_rationale,
            points_status=points_status,
        )


class StoryPointsReviewResponse(BaseModel):
    id: int
    story_points: int
    points_status: str
    points_reviewed_by: int
    points_reviewed_at: datetime
