from pydantic import BaseModel, Field

from app.schemas.feature_schema import FeatureResponse
from app.schemas.story_schema import StoryResponse
from app.schemas.sub_feature_schema import SubFeatureResponse
from app.schemas.test_case_schema import TestCaseResponse


class StatusCounts(BaseModel):
    total: int = 0
    approved: int = 0
    pending_review: int = 0
    rejected: int = 0
    other: int = 0


class StageSummary(BaseModel):
    id: str
    status: str
    counts: StatusCounts | None = None
    pending: int = 0
    lock_reason: str | None = None


class PipelineBlocker(BaseModel):
    feature_id: int
    feature_title: str
    unanswered: int


class SuggestedStep(BaseModel):
    label: str
    action: str | None = None
    stage_id: str


class PipelineTotals(BaseModel):
    pending_review: int = 0
    approved_stories: int = 0


class PipelineSummaryResponse(BaseModel):
    brd_id: int
    brd_status: str
    stages: dict[str, StageSummary]
    blockers: list[PipelineBlocker] = Field(default_factory=list)
    suggested_step: SuggestedStep
    totals: PipelineTotals


class PipelineTreeResponse(BaseModel):
    """Full workspace tree in one response (avoids N+1 list fan-out)."""

    brd_id: int
    features: list[FeatureResponse] = Field(default_factory=list)
    sub_features: list[SubFeatureResponse] = Field(default_factory=list)
    stories: list[StoryResponse] = Field(default_factory=list)
    test_cases: list[TestCaseResponse] = Field(default_factory=list)
