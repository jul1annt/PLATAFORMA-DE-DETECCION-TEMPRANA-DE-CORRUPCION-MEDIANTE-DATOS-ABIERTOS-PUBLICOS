"""PostgreSQL integration coverage for persisted administrator sessions."""

from __future__ import annotations

import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from main import app
from modules.auth.repository.AuthRepository import AuthRepository
from modules.auth.dto.request import LoginRequest
from shared.errors import AuthError
from modules.auth.model.Admin import Admin
from modules.auth.model.AdminSession import AdminSession
from modules.auth.service import AuthService as auth_service_module
from modules.auth.service.AuthService import AuthService


@pytest.fixture
def auth_client(postgres_test_session):
    def override_get_db():
        yield postgres_test_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


def _create_admin(session: Session, *, is_active: bool = True) -> Admin:
    suffix = uuid.uuid4().hex
    admin = Admin(
        username=f"auth-test-{suffix}",
        email=f"auth-test-{suffix}@example.test",
        hashed_password=AuthService(session).hash_password("test-password-123"),
        is_active=is_active,
    )
    session.add(admin)
    session.flush()
    return admin


def test_login_me_and_logout_revoke_persisted_session(auth_client, postgres_test_session):
    admin = _create_admin(postgres_test_session)
    response = auth_client.post(
        "/api/auth/login",
        json={"username": admin.username, "password": "test-password-123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert auth_client.get("/api/auth/me", headers=headers).status_code == 200
    assert auth_client.post("/api/auth/logout", headers=headers).status_code == 200
    assert auth_client.get("/api/auth/me", headers=headers).status_code == 401


def test_concurrent_failed_logins_respect_shared_attempt_limit(
    postgres_test_session, monkeypatch
):
    engine = create_engine(os.environ["TEST_DATABASE_URL"], pool_size=12, max_overflow=0)
    monkeypatch.setattr(auth_service_module.settings, "LOGIN_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(auth_service_module.settings, "LOGIN_WINDOW_MINUTES", 15)
    original_count = AuthRepository.count_recent_failures

    def slow_count(repository, login_key, since):
        count = original_count(repository, login_key, since)
        # Widen the check/record race that allowed simultaneous requests to
        # exceed the threshold before the transaction-scoped lock was added.
        time.sleep(0.03)
        return count

    monkeypatch.setattr(AuthRepository, "count_recent_failures", slow_count)
    username = f"parallel-{uuid.uuid4().hex}"
    request = LoginRequest(username=username, password="incorrect-password")

    def failed_login() -> int:
        with Session(engine) as session:
            try:
                AuthService(session).login(request, client_ip="192.0.2.45")
            except AuthError as exc:
                return {"bad_credentials": 401, "rate_limited": 429}[exc.code]
        raise AssertionError("El login inválido no rechazó la solicitud")

    try:
        with ThreadPoolExecutor(max_workers=12) as pool:
            statuses = list(pool.map(lambda _index: failed_login(), range(12)))
    finally:
        with Session(engine) as cleanup_session:
            key = AuthService(cleanup_session)._login_key(username, "192.0.2.45")
            AuthRepository(cleanup_session).clear_failures(key)
        engine.dispose()

    assert statuses.count(401) == 3
    assert statuses.count(429) == 9


@pytest.mark.parametrize("failure", ["expired", "revoked", "inactive"])
def test_api_rejects_expired_revoked_and_inactive_admin_sessions(
    auth_client, postgres_test_session, failure
):
    admin = _create_admin(postgres_test_session, is_active=failure != "inactive")
    service = AuthService(postgres_test_session)
    token, jti, expires_at = service.create_access_token(admin.id, admin.username)

    if failure == "expired":
        token = jwt.encode(
            {
                "sub": str(admin.id),
                "username": admin.username,
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
                "type": "admin",
                "jti": jti,
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

    postgres_test_session.add(AdminSession(
        jti=jti,
        admin_id=admin.id,
        expires_at=expires_at,
        revoked=failure == "revoked",
    ))
    postgres_test_session.flush()

    response = auth_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
