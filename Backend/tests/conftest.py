"""Shared fixtures for isolated PostgreSQL integration tests."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


@pytest.fixture
def postgres_test_session():
    """Provide a rollback-isolated session only for explicit loopback test DBs."""
    url_text = os.getenv("TEST_DATABASE_URL")
    if not url_text:
        pytest.skip("TEST_DATABASE_URL no está configurada")

    url = make_url(url_text)
    if url.get_backend_name() != "postgresql":
        pytest.fail("TEST_DATABASE_URL debe apuntar a PostgreSQL")
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("TEST_DATABASE_URL debe usar un host loopback")
    if "test" not in (url.database or "").lower():
        pytest.fail("El nombre de la base TEST_DATABASE_URL debe contener 'test'")

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            session = Session(bind=connection, join_transaction_mode="create_savepoint")
            try:
                yield session
            finally:
                session.close()
                transaction.rollback()
    finally:
        engine.dispose()
