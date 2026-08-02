from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.mixins import CONFIRM_PASSWORD_FIELD, PASSWORD_FIELD, PasswordMixin


class UserRegisterRequest(PasswordMixin, BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = PASSWORD_FIELD
    confirm_password: str = CONFIRM_PASSWORD_FIELD

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(...)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., examples=["user@example.com"])

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = Field(
        default=None,
        description="Only returned when DEBUG=true (local development)",
    )


class PasswordResetConfirmRequest(PasswordMixin, BaseModel):
    token: str = Field(..., description="Reset token from forgot-password flow")
    password: str = PASSWORD_FIELD
    confirm_password: str = CONFIRM_PASSWORD_FIELD


class UserPasswordChangeRequest(PasswordMixin, BaseModel):
    current_password: str = Field(...)
    password: str = PASSWORD_FIELD
    confirm_password: str = CONFIRM_PASSWORD_FIELD


class MessageResponse(BaseModel):
    message: str


from app.schemas.user_schema import UserResponse  # noqa: E402

LoginResponse.model_rebuild()
