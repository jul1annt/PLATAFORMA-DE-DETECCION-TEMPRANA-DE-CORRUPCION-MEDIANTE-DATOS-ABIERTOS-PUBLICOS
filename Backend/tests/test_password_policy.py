import pytest
from shared.errors import AuthError
from pydantic import ValidationError

from modules.auth.dto.request import CreateAdminRequest, LoginRequest
from modules.auth.service.AuthService import AuthService


def test_new_admin_password_enforces_policy_without_normalizing_valid_spaces():
    original = "  safe passphrase 12  "
    request = CreateAdminRequest(
        username="operator",
        email="operator@example.com",
        password=original,
    )

    assert request.password == original
    assert CreateAdminRequest(
        username="operator",
        email="operator@example.com",
        password="x" * 128,
    ).password == "x" * 128


@pytest.mark.parametrize("password", ["x" * 11, "x" * 129, " " * 12, "valid-password\n12"])
def test_new_admin_password_rejects_short_long_blank_or_control_values(password):
    with pytest.raises(ValidationError):
        CreateAdminRequest(
            username="operator",
            email="operator@example.com",
            password=password,
        )


@pytest.mark.parametrize("password", ["x" * 7, "x" * 129, " " * 8, "valid-pass\tword"])
def test_login_password_rejects_malformed_values_without_truncation(password):
    with pytest.raises(ValidationError):
        LoginRequest(username="operator", password=password)


def test_service_rechecks_password_even_if_pydantic_validation_was_bypassed():
    service = AuthService.__new__(AuthService)
    service.repository = object()
    request = CreateAdminRequest.model_construct(
        username="operator",
        email="operator@example.com",
        password=" " * 12,
    )

    with pytest.raises(AuthError) as failure:
        service.create_admin(request)

    assert failure.value.code == "malformed_password"
