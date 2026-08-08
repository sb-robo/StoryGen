from datetime import datetime

from pydantic import BaseModel, Field


class LlmCallLogResponse(BaseModel):
    id: int
    operation_id: str | None = None
    brd_id: int | None = None
    node_name: str
    iteration: int
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    created_at: datetime


class LlmNodeUsage(BaseModel):
    node_name: str
    calls: int
    tokens_in: int
    tokens_out: int
    latency_ms: int


class LlmUsageSummaryResponse(BaseModel):
    brd_id: int
    total_calls: int
    total_tokens_in: int
    total_tokens_out: int
    total_latency_ms: int
    by_node: list[LlmNodeUsage] = Field(default_factory=list)
    recent_calls: list[LlmCallLogResponse] = Field(default_factory=list)
