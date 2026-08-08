from datetime import datetime
from enum import StrEnum
from math import ceil

from pydantic import BaseModel, ConfigDict, Field


class FeatureStatusFilter(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ClarifyingAnswer(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class FeatureResponse(BaseModel):
    id: int
    brd_id: int
    user_id: int
    operation_id: str | None = None
    title: str
    description: str
    confidence: float
    rationale: str
    clarifying_questions: list[str] = Field(default_factory=list)
    clarifying_answers: list[ClarifyingAnswer] = Field(default_factory=list)
    source_excerpt: str | None = None
    status: str
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeatureListResponse(BaseModel):
    brd_id: int
    items: list[FeatureResponse]
    total: int

    @classmethod
    def build(
        cls, *, brd_id: int, items: list[FeatureResponse]
    ) -> "FeatureListResponse":
        return cls(brd_id=brd_id, items=items, total=len(items))


class FeatureExtractionResultResponse(BaseModel):
    brd_id: int
    operation_id: str
    features: list[FeatureResponse]
    total: int

    @classmethod
    def build(
        cls,
        *,
        brd_id: int,
        operation_id: str,
        features: list[FeatureResponse],
    ) -> "FeatureExtractionResultResponse":
        return cls(
            brd_id=brd_id,
            operation_id=operation_id,
            features=features,
            total=len(features),
        )


class FeatureUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = Field(default=None, min_length=1)
    clarifying_questions: list[str] | None = None
    clarifying_answers: list[ClarifyingAnswer] | None = None


class FeatureReviewResponse(BaseModel):
    id: int
    status: str
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
