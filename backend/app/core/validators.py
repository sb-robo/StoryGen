import re


def validate_password_strength(password: str) -> str:
    if not password.strip():
        raise ValueError("password cannot be empty")

    if len(password) < 8 or len(password) > 25:
        raise ValueError("password length should be 8 to 25 characters")

    if not re.search(r"[A-Z]", password):
        raise ValueError("password must contain atleast one uppercase letter")

    if not re.search(r"[a-z]", password):
        raise ValueError("password must contain atleast one lowercase letter")

    if not re.search(r"\d", password):
        raise ValueError("password must contain a number")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError("password must contain at least one special character")

    return password
