from pydantic import BaseModel, field_validator, model_validator, Field
from app.core.validators import validate_password_strength


class PasswordMixin(BaseModel):
    password: str = Field(...)
    confirm_password: str = Field(...)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def password_match(self):
        if self.password != self.confirm_password:
            raise ValueError("password didn't match")

        return self
