from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationInfo
from app.core.validators import validate_password_strength


class UserCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(...)
    confirm_password: str = Field(...)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("confirm_password")
    @classmethod
    def password_match(cls, v: str, info: ValidationInfo) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("passwords do not match")

        return v
