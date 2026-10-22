"""Unit coverage for the shared login-attempt throttle."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from shared.errors import AuthError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from modules.auth.dto.request import LoginRequest
from modules.auth.repository.AuthRepository import AuthRepository
from modules.auth.service import AuthService as service_module
from modules.auth.service.AuthService import AuthService


def test_login_serializes_check_and_failure_record(monkeypatch):
    events = []

    class Repository:
        def __init__(self, _db):
            self.failures = 0

        def lock_login_attempts(self, login_key):
            events.append(("lock", login_key))

        def count_recent_failures(self, login_key, _since):
            events.append(("count", login_key))
            return self.failures

        def get_by_username(self, _username):
            events.append(("lookup",))
            return None

        def record_failure(self, login_key):
            events.append(("record", login_key))
            self.failures += 1

    monkeypatch.setattr(service_module, "AuthRepository", Repository)
    monkeypatch.setattr(service_module.settings, "LOGIN_MAX_ATTEMPTS", 2)
    service = AuthService(object())
    request = LoginRequest(username="operator", password="wrong-password")

    for _ in range(2):
        with pytest.raises(AuthError) as failure:
            service.login(request, client_ip="192.0.2.8")
        assert failure.value.code == "bad_credentials"

    with pytest.raises(AuthError) as limited:
        service.login(request, client_ip="192.0.2.8")

    assert limited.value.code == "rate_limited"
    assert [event[0] for event in events] == [
        "lock", "count", "lookup", "record",
        "lock", "count", "lookup", "record",
        "lock", "count",
    ]
    assert len({event[1] for event in events if len(event) > 1}) == 1


def test_repository_uses_transaction_scoped_postgres_lock():
    class Database:
        call = None

        def execute(self, statement, parameters):
            self.call = (str(statement), parameters)

    db = Database()
    AuthRepository(db).lock_login_attempts("f" * 64)

    statement, parameters = db.call
    assert "pg_advisory_xact_lock" in statement
    assert -(2**63) <= parameters["lock_key"] < 2**63


def test_successful_login_clears_failures_and_creates_revocable_session(monkeypatch):
    class Repository:
        failures = 2
        cleared = False
        created_session = None

        def lock_login_attempts(self, _key):
            pass

        def count_recent_failures(self, _key, _since):
            return self.failures

        def get_by_username(self, _username):
            return SimpleNamespace(id=7, username="operator", hashed_password="hash")

        def clear_failures(self, _key):
            self.failures = 0
            self.cleared = True

        def create_session(self, session):
            self.created_session = session

    monkeypatch.setattr(service_module, "AuthRepository", lambda _db: Repository())
    monkeypatch.setattr(service_module.settings, "LOGIN_MAX_ATTEMPTS", 3)
    service = AuthService(object())
    service.verify_password = lambda _plain, _hashed: True
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    service.create_access_token = lambda _admin_id, _username: ("jwt", "jti-7", expires_at)

    result = service.login(LoginRequest(username="operator", password="valid-password"))

    assert result.access_token == "jwt"
    assert service.repository.failures == 0
    assert service.repository.cleared is True
    assert service.repository.created_session.jti == "jti-7"
    assert service.repository.created_session.admin_id == 7


def test_repository_expires_old_failures_and_can_reset_the_window():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    now = datetime.now(timezone.utc)
    timestamp = lambda value: value.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S.%f")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE login_attempts (
                id INTEGER PRIMARY KEY,
                login_key VARCHAR(64) NOT NULL,
                attempted_at DATETIME NOT NULL
            )
        """))
        connection.execute(text(
            "INSERT INTO login_attempts (id, login_key, attempted_at) VALUES (:id, :key, :at)"
        ), [
            {"id": 1, "key": "user-a", "at": timestamp(now - timedelta(minutes=16))},
            {"id": 2, "key": "user-a", "at": timestamp(now - timedelta(minutes=3))},
            {"id": 3, "key": "user-b", "at": timestamp(now - timedelta(minutes=2))},
        ])

    try:
        with Session(engine) as session:
            repository = AuthRepository(session)
            assert repository.count_recent_failures("user-a", now - timedelta(minutes=15)) == 1
            repository.clear_failures("user-a")
            assert repository.count_recent_failures("user-a", now - timedelta(minutes=15)) == 0
            assert repository.count_recent_failures("user-b", now - timedelta(minutes=15)) == 1
    finally:
        engine.dispose()
