from pydantic import Field, field_validator, model_validator

from app.utils.validators import validate_password_strength

PASSWORD_FIELD = Field(...)
CONFIRM_PASSWORD_FIELD = Field(...)


class PasswordMixin:
    """
    Shared password validation for models that define `password` and `confirm_password`.

    Fields are declared on each subclass (not here) so Swagger/OpenAPI lists them
    in the order you want — Pydantic puts inherited fields before subclass fields.
    """

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def password_match(self):
        if self.password != self.confirm_password:
            raise ValueError("password didn't match")

        return self
