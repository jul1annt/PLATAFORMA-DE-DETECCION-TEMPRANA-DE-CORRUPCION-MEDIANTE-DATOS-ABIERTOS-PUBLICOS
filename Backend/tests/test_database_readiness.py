from threading import Lock
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.engine import URL

from core.config import Settings
from core.database_readiness import prepare_database_pool


class FakeConnection:
    def __init__(self, engine, pid):
        self.engine, self.pid = engine, pid

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.engine.closed.append(self.pid)

    def execute(self, statement):
        self.engine.statements.append(str(statement))
        return self

    def mappings(self):
        return self

    def one(self):
        row = dict(database="fixture", role="app", address="127.0.0.1", port=5432,
                    pid=self.pid, rolsuper=False, rolcreatedb=False,
                    rolcreaterole=False, rolreplication=False)
        row.update(self.engine.overrides)
        return row


class FakeEngine:
    def __init__(self):
        self.url = URL.create("postgresql", username="app", host="127.0.0.1", port=5432, database="fixture")
        self.pool = SimpleNamespace(size=lambda: 10)
        self.lock = Lock()
        self.pids, self.closed, self.statements = [], [], []
        self.overrides = {}
        self.failure = False

    def connect(self):
        with self.lock:
            if self.failure:
                raise RuntimeError("credential-value-must-not-be-emitted")
            pid = 100 + len(self.pids)
            self.pids.append(pid)
        return FakeConnection(self, pid)


def configured(**overrides):
    values = dict(DB_HOST="127.0.0.1", DB_PORT=5432, DB_USER="app", DB_PASSWORD="fixture-only",
                  DB_NAME="fixture", SECRET_KEY="s" * 48, ENCRYPTION_KEY=Fernet.generate_key().decode(),
                  DB_POOL_PREWARM=0, DB_POOL_MAX_OVERFLOW=20, DB_CONNECT_TIMEOUT_SECONDS=60)
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_disabled_readiness_does_not_touch_engine():
    assert prepare_database_pool(None, 0) == 0


@pytest.mark.parametrize("count", [-1, 11, True, False, 1.5])
def test_readiness_rejects_invalid_count(count):
    with pytest.raises(ValueError):
        prepare_database_pool(FakeEngine(), count)


def test_readiness_prepares_distinct_slots_and_closes_transactions():
    engine = FakeEngine()
    assert prepare_database_pool(engine, 10) == 10
    assert len(set(engine.pids)) == len(engine.closed) == 10
    assert engine.statements.count("SET TRANSACTION READ ONLY") == 10
    assert all("INSERT" not in x and "UPDATE" not in x and "DELETE" not in x for x in engine.statements)
    assert all("host(inet_server_addr())" in x for x in engine.statements if x.startswith("SELECT"))


@pytest.mark.parametrize("override", [dict(database="other"), dict(role="other"), dict(address="8.8.8.8"),
                                      dict(port=6543), dict(rolsuper=True), dict(rolcreatedb=True),
                                      dict(rolcreaterole=True), dict(rolreplication=True)])
def test_readiness_rejects_wrong_identity_and_privilege(override):
    engine = FakeEngine()
    engine.overrides = override
    with pytest.raises(RuntimeError, match="No se completó"):
        prepare_database_pool(engine, 2)
    assert len(engine.closed) == len(engine.pids)


def test_failed_connect_is_sanitized_and_barrier_aborted():
    engine = FakeEngine()
    engine.failure = True
    with pytest.raises(RuntimeError) as error:
        prepare_database_pool(engine, 2)
    assert "credential-value" not in str(error.value)


def test_remote_engine_is_rejected_before_connecting():
    engine = FakeEngine()
    engine.url = engine.url.set(host="8.8.8.8")
    with pytest.raises(ValueError):
        prepare_database_pool(engine, 2)
    assert not engine.pids


@pytest.mark.parametrize("overrides", [dict(DB_POOL_PREWARM=11), dict(DB_POOL_PREWARM=-1),
                                     dict(DB_POOL_MAX_OVERFLOW=-1), dict(DB_CONNECT_TIMEOUT_SECONDS=0),
                                     dict(DB_POOL_PREWARM=10, DB_POOL_MAX_OVERFLOW=20),
                                     dict(DB_POOL_PREWARM=10, DB_POOL_MAX_OVERFLOW=0, DB_HOST="8.8.8.8"),
                                     dict(DB_POOL_PREWARM=10, DB_POOL_MAX_OVERFLOW=0, DB_CONNECT_TIMEOUT_SECONDS=61)])
def test_settings_reject_invalid_pool_policy(overrides):
    with pytest.raises(ValueError):
        configured(**overrides)


def test_settings_accept_bounded_local_readiness():
    settings = configured(DB_POOL_PREWARM=10, DB_POOL_MAX_OVERFLOW=0)
    assert settings.DB_POOL_PREWARM == 10 and settings.DB_CONNECT_TIMEOUT_SECONDS == 60


def test_small_pool_is_rejected_before_connecting():
    engine = FakeEngine()
    engine.pool.size = lambda: 1
    with pytest.raises(ValueError):
        prepare_database_pool(engine, 2)
    assert not engine.pids


def test_duplicate_backend_is_not_counted_as_multiple_slots():
    engine = FakeEngine()
    engine.overrides = {"pid": 1}
    with pytest.raises(RuntimeError, match="independientes"):
        prepare_database_pool(engine, 2)
    assert len(engine.closed) == 2


def test_lifespan_waits_for_preparation_before_ready(monkeypatch):
    import main
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    called = []
    monkeypatch.setattr(main.settings, "DB_POOL_PREWARM", 10)
    def prepared(engine, count):
        called.append((engine, count))
        return count
    monkeypatch.setattr(main, "prepare_database_pool", prepared)
    app = FastAPI(lifespan=main.lifespan)
    with TestClient(app):
        assert called == [(main.engine, 10)]
        assert app.state.prepared_db_connections == 10


def test_lifespan_does_not_become_ready_after_failure(monkeypatch):
    import main
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    monkeypatch.setattr(main.settings, "DB_POOL_PREWARM", 10)
    def failed(*_):
        raise RuntimeError("preparation failed")
    monkeypatch.setattr(main, "prepare_database_pool", failed)
    app = FastAPI(lifespan=main.lifespan)
    with pytest.raises(RuntimeError, match="preparation failed"):
        with TestClient(app):
            pytest.fail("Startup must fail before serving")
    assert not hasattr(app.state, "prepared_db_connections")
