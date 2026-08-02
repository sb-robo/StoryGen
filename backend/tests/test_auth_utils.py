from app.utils.password_handler import hash_password, verify_password
from app.utils.token_hash import hash_token
from app.utils.validators import validate_password_strength


def test_password_strength_valid():
    assert validate_password_strength("Password1!") == "Password1!"


def test_password_strength_rejects_weak():
    try:
        validate_password_strength("weak")
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_hash_and_verify_password():
    hashed = hash_password("Password1!")
    assert verify_password("Password1!", hashed) is True
    assert verify_password("WrongPassword1!", hashed) is False


def test_hash_token_is_deterministic():
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("xyz")
