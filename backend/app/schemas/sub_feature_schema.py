from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ReviewStatusFilter(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class SubFeatureResponse(BaseModel):
    id: int
    feature_id: int
    user_id: int
    operation_id: str | None = None
    title: str
    description: str
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


class SubFeatureListResponse(BaseModel):
    feature_id: int
    items: list[SubFeatureResponse]
    total: int

    @classmethod
    def build(
        cls, *, feature_id: int, items: list[SubFeatureResponse]
    ) -> "SubFeatureListResponse":
        return cls(feature_id=feature_id, items=items, total=len(items))


class SubFeatureGenerationResultResponse(BaseModel):
    feature_id: int
    operation_id: str
    sub_features: list[SubFeatureResponse]
    total: int

    @classmethod
    def build(
        cls,
        *,
        feature_id: int,
        operation_id: str,
        sub_features: list[SubFeatureResponse],
    ) -> "SubFeatureGenerationResultResponse":
        return cls(
            feature_id=feature_id,
            operation_id=operation_id,
            sub_features=sub_features,
            total=len(sub_features),
        )


class SubFeatureUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = Field(default=None, min_length=1)


class SubFeatureReviewResponse(BaseModel):
    id: int
    status: str
    reviewed_by: int
    reviewed_at: datetime
