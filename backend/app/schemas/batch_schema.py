from pydantic import BaseModel, Field

from app.schemas.operation_schema import OperationResponse


class BatchSkippedItem(BaseModel):
    resource_type: str
    resource_id: int
    reason: str


class BatchOperationResponse(BaseModel):
    brd_id: int
    action: str
    operations: list[OperationResponse] = Field(default_factory=list)
    total: int = 0
    skipped: list[BatchSkippedItem] = Field(default_factory=list)
