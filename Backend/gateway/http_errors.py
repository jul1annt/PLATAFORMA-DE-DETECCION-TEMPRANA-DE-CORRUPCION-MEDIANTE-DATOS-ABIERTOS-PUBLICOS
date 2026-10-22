"""Map application failures to the public HTTP contract at the API boundary."""

from fastapi import Request
from fastapi.responses import JSONResponse

from shared.errors import AuthError, IngestaError

AUTH_STATUS = {
    "invalid_token": 401,
    "expired_token": 401,
    "malformed_password": 422,
    "rate_limited": 429,
    "bad_credentials": 401,
    "duplicate_admin": 409,
    "duplicate_username": 409,
    "duplicate_email": 409,
    "session_invalid": 401,
    "admin_missing": 401,
}
INGESTA_STATUS = {
    "source_exists": 409,
    "source_missing": 404,
    "sync_locked": 409,
    "sync_failed": 502,
}


async def auth_error_response(_request: Request, error: AuthError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if error.code in {"expired_token", "session_invalid"} else None
    return JSONResponse(status_code=AUTH_STATUS[error.code], content={"detail": error.detail}, headers=headers)


async def ingesta_error_response(_request: Request, error: IngestaError) -> JSONResponse:
    return JSONResponse(status_code=INGESTA_STATUS[error.code], content={"detail": error.detail})
