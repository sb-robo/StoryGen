from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.schemas.mixins import PasswordMixin


class UserRegisterRequest(PasswordMixin):
    name: str = Field(..., min_length=3, max_length=100)
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(...)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserPasswordChangeRequest(PasswordMixin):
    current_password: str = Field(...)


class ResetPasswordRequest(PasswordMixin):
    pass
