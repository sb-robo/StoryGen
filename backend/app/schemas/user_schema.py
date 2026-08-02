from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    skip: int
    limit: int


class UserUpdateRequest(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
        description="Updated display name",
        examples=["Suraj Biswas"],
    )
    email: EmailStr | None = Field(
        default=None,
        description="Updated email address",
        examples=["suraj@example.com"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"name": "Suraj Biswas"},
                {"email": "suraj.new@example.com"},
                {"name": "Suraj Biswas", "email": "suraj.new@example.com"},
            ]
        }
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip().lower()

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if self.name is None and self.email is None:
            raise ValueError("Provide at least one field to update: name or email")

        return self


class AdminUserUpdateRequest(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
        description="Updated display name for the user",
        examples=["Jane Doe"],
    )
    is_active: bool | None = Field(
        default=None,
        description="Set to false to deactivate the account, true to reactivate",
        examples=[True],
    )
    is_admin: bool | None = Field(
        default=None,
        description="Grant or revoke admin access",
        examples=[False],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"name": "Jane Doe"},
                {"is_active": False},
                {"is_admin": True, "is_active": True},
            ]
        }
    )

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip()

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if self.name is None and self.is_active is None and self.is_admin is None:
            raise ValueError("Provide at least one field to update: name, is_active, or is_admin")

        return self
