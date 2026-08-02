from app.schemas.user_schema import AdminUserUpdateRequest, UserUpdateRequest
import pytest


def test_user_update_requires_one_field():
    with pytest.raises(ValueError):
        UserUpdateRequest()


def test_admin_update_requires_one_field():
    with pytest.raises(ValueError):
        AdminUserUpdateRequest()


def test_user_update_accepts_name_only():
    req = UserUpdateRequest(name="Suraj Biswas")
    assert req.name == "Suraj Biswas"
    assert req.email is None
