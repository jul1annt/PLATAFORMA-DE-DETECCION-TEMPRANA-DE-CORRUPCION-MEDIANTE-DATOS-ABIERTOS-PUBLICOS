from time import time
from uuid import uuid4

import jwt
import pytest
from shared.errors import AuthError

from core.config import settings
from modules.auth.config.settings import ALGORITHM
from modules.auth.service.AuthService import AuthService


@pytest.mark.parametrize("missing_claim", ["exp", "sub", "jti", "type"])
def test_signed_admin_token_requires_all_security_claims(missing_claim):
    claims = {
        "exp": int(time()) + 3600,
        "sub": "7",
        "jti": str(uuid4()),
        "type": "admin",
    }
    del claims[missing_claim]
    token = jwt.encode(claims, settings.SECRET_KEY, algorithm=ALGORITHM)

    service = AuthService.__new__(AuthService)
    with pytest.raises(AuthError) as failure:
        service.decode_token(token)

    assert failure.value.code == "expired_token"


def test_signed_non_object_jwt_payload_is_unauthorized():
    token = jwt.api_jws.encode(b"[]", settings.SECRET_KEY, algorithm=ALGORITHM)

    service = AuthService.__new__(AuthService)
    with pytest.raises(AuthError) as failure:
        service.decode_token(token)

    assert failure.value.code == "expired_token"


def test_signed_admin_token_with_non_numeric_subject_is_unauthorized():
    token = jwt.encode(
        {
            "exp": int(time()) + 3600,
            "sub": "not-an-admin-id",
            "jti": str(uuid4()),
            "type": "admin",
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )

    service = AuthService.__new__(AuthService)
    with pytest.raises(AuthError) as failure:
        service.decode_token(token)

    assert failure.value.code == "expired_token"


def test_valid_session_for_inactive_admin_is_unauthorized():
    service = AuthService.__new__(AuthService)
    service.decode_token = lambda _token: {"sub": "19", "jti": str(uuid4())}

    class Repository:
        def get_active_session(self, jti, now):
            assert jti
            assert now.tzinfo is not None
            return object()

        def get_by_id(self, admin_id, *, active_only):
            assert admin_id == 19
            assert active_only is True
            return None

    service.repository = Repository()

    with pytest.raises(AuthError) as failure:
        service.get_current_admin("valid-token")

    assert failure.value.code == "admin_missing"
