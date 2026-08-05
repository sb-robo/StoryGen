from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field


class OperationStatusValue(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class OperationResponse(BaseModel):
    operation_id: str = Field(description="Poll this id for status and result")
    operation_type: str
    status: str
    resource_type: str | None = None
    resource_id: int | None = Field(
        default=None, description="BRD id once the upload row exists"
    )
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
        return f"/api/v1/brds/status/{self.operation_id}"

    @computed_field
    @property
    def result_url(self) -> str:
        return f"/api/v1/brds/result/{self.operation_id}"


class OperationResultResponse(BaseModel):
    operation_id: str
    status: str
    resource_type: str | None = None
    resource_id: int | None = None
    result: dict | None = Field(
        default=None,
        description="BRD detail payload when operation succeeded",
    )
