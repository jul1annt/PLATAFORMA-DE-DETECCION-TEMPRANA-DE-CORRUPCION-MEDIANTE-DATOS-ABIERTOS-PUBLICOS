import asyncio
import json

from gateway.http_errors import auth_error_response, ingesta_error_response
from shared.errors import AuthError, IngestaError


def test_auth_errors_keep_public_status_detail_and_bearer_header():
    response = asyncio.run(auth_error_response(None, AuthError("session_invalid", "Sesión revocada o expirada")))
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert json.loads(response.body) == {"detail": "Sesión revocada o expirada"}


def test_ingesta_errors_keep_public_status_and_detail():
    response = asyncio.run(ingesta_error_response(None, IngestaError("sync_failed", "Fallo en sincronización")))
    assert response.status_code == 502
    assert json.loads(response.body) == {"detail": "Fallo en sincronización"}
