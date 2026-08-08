from pydantic import BaseModel, Field


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
