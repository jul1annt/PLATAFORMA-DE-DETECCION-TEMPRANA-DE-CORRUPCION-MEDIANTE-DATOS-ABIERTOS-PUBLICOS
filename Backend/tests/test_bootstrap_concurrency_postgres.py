from concurrent.futures import ThreadPoolExecutor
import os
from threading import Event
import time
import uuid

import pytest
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from modules.auth.dto.request import CreateAdminRequest
from modules.auth.model.Admin import Admin
from scripts import create_first_admin as bootstrap


def test_concurrent_initial_admin_bootstrap_creates_exactly_one(postgres_test_session, monkeypatch):
    # The shared fixture validates that this is an explicit, loopback test DB.
    assert postgres_test_session.query(Admin).count() == 0
    url = make_url(os.environ["TEST_DATABASE_URL"])
    app_name = f"bootstrap-test-{uuid.uuid4().hex}"
    worker_engine = create_engine(
        url, connect_args={"application_name": app_name}, pool_size=2, max_overflow=0
    )
    observer_engine = create_engine(url, pool_size=1, max_overflow=0)
    usernames = [f"bootstrap-{uuid.uuid4().hex[:16]}" for _ in range(2)]
    emails = [f"{username}@example.com" for username in usernames]
    acquired_lock = Event()
    release_first = Event()
    started = [Event(), Event()]
    executor = ThreadPoolExecutor(max_workers=2)

    real_create_locked = bootstrap._create_first_admin_locked

    def pause_first_holder(db, request):
        if not acquired_lock.is_set():
            acquired_lock.set()
            assert release_first.wait(timeout=10), "no se liberó la pausa del primer bootstrap"
        return real_create_locked(db, request)

    monkeypatch.setattr(bootstrap, "_create_first_admin_locked", pause_first_holder)

    try:
        def attempt(index: int):
            started[index].set()
            with Session(worker_engine) as db:
                request = CreateAdminRequest(
                    username=usernames[index],
                    email=emails[index],
                    password="concurrent-test-password",
                )
                try:
                    return ("created", bootstrap.create_first_admin(db, request).username)
                except SystemExit as exc:
                    return ("rejected", str(exc))

        futures = [executor.submit(attempt, index) for index in range(2)]
        if not acquired_lock.wait(timeout=10):
            errors = [repr(future.exception()) for future in futures if future.done()]
            pytest.fail(f"ningún bootstrap adquirió el bloqueo; errores de tareas: {errors}")
        assert all(event.wait(timeout=10) for event in started)
        deadline = time.monotonic() + 10
        waiting = 0
        while time.monotonic() < deadline:
            with observer_engine.connect() as observer:
                waiting = observer.execute(text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE application_name = :app AND wait_event_type = 'Lock'"
                ), {"app": app_name}).scalar_one()
            if waiting == 1:
                break
            time.sleep(0.05)
        assert waiting == 1, "el segundo intento no quedó esperando el bloqueo de bootstrap"
        release_first.set()

        results = [future.result(timeout=20) for future in futures]
        assert sum(outcome == "created" for outcome, _ in results) == 1
        assert sum(outcome == "rejected" for outcome, _ in results) == 1
        assert all("already exists" in detail for outcome, detail in results if outcome == "rejected")
        created_count = postgres_test_session.execute(
                select(func.count()).select_from(Admin).where(Admin.username.in_(usernames))
        ).scalar_one()
        assert created_count == 1
    finally:
        release_first.set()
        executor.shutdown(wait=True, cancel_futures=True)
        with worker_engine.begin() as cleanup:
            cleanup.execute(delete(Admin).where(Admin.username.in_(usernames)))
        observer_engine.dispose()
        worker_engine.dispose()
