from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from core.config import Settings, settings
from core.database import get_db
from core.read_database import apply_read_parallelism, get_provider_db, get_search_db
from core.public_database import get_public_db,get_public_search_db,get_public_provider_db
from modules.transformacion.controller.transformacionController import router


def test_unconfigured_read_policy_does_not_access_the_database():
    db = object()
    assert apply_read_parallelism(db, None) is db


@pytest.mark.parametrize('workers', [0, 1, 2, 1024])
def test_read_limit_uses_bound_parameters_and_transaction_local_setting(workers):
    calls = []
    db = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name='postgresql')),
        execute=lambda sql, params: calls.append((str(sql), params)),
    )
    assert apply_read_parallelism(db, workers) is db
    assert calls == [("SELECT set_config('max_parallel_workers_per_gather', :workers, true)", {'workers': str(workers)})]


@pytest.mark.parametrize('workers', [-1, 1025, True, '0', 1.5])
def test_read_policy_rejects_invalid_limits_before_accessing_db(workers):
    with pytest.raises(ValueError):
        apply_read_parallelism(object(), workers)


def test_read_policy_leaves_sqlite_unchanged():
    engine = create_engine('sqlite://')
    try:
        with Session(engine) as db:
            assert apply_read_parallelism(db, 0) is db
            assert db.execute(text('SELECT 1')).scalar_one() == 1
    finally:
        engine.dispose()


@pytest.mark.parametrize('field', ['SEARCH_QUERY_PARALLEL_WORKERS', 'PROVIDER_QUERY_PARALLEL_WORKERS'])
def test_settings_accept_optional_zero_and_reject_out_of_range_limits(field):
    values = settings.model_dump()
    assert Settings(**{**values, field: 0}).model_dump()[field] == 0
    assert Settings(**{**values, field: None}).model_dump()[field] is None
    for value in (-1, 1025):
        with pytest.raises(ValidationError):
            Settings(**{**values, field: value})


def test_route_limits_are_independent(monkeypatch):
    calls = []
    db = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name='postgresql')),
        execute=lambda sql, params: calls.append(params['workers']),
    )
    monkeypatch.setattr(settings, 'SEARCH_QUERY_PARALLEL_WORKERS', 0)
    monkeypatch.setattr(settings, 'PROVIDER_QUERY_PARALLEL_WORKERS', 1)
    assert get_search_db(db) is db
    assert get_provider_db(db) is db
    assert calls == ['0', '1']


def test_only_the_measured_routes_use_the_optional_read_policy():
    roots = {route.path: next(p for p in route.dependant.dependencies if p.name == 'db').call for route in router.routes if 'db' in route.endpoint.__annotations__}
    assert roots['/procesados/search'] is get_public_search_db
    assert roots['/procesados/metricas/top-proveedores'] is get_public_provider_db
    admin={'/procesados/reprocesar','/procesados/logs','/procesados/logs/export/{formato}','/procesados/export/{formato}/jobs',
           '/procesados/admin/metricas/calidad','/procesados/admin/metricas/campos-faltantes'}
    assert all(call is get_db for path,call in roots.items() if path in admin)
    assert all(call is get_public_db for path,call in roots.items() if path not in admin|{'/procesados/search','/procesados/metricas/top-proveedores'})
    for path in ('/procesados/search', '/procesados/metricas/top-proveedores'):
        route = next(route for route in router.routes if route.path == path)
        db_dependency = next(p for p in route.dependant.dependencies if p.name == 'db')
        assert db_dependency.dependencies[0].call is get_public_db
        assert next(p for p in db_dependency.dependencies[0].dependencies if p.name=='db').call is get_db


@pytest.mark.parametrize('finish', ['rollback', 'commit', 'exception'])
def test_native_read_limit_does_not_leak_to_reused_connection(postgres_test_session, monkeypatch, finish):
    from core import database
    engine = create_engine(postgres_test_session.connection().engine.url, pool_size=1, max_overflow=0)
    monkeypatch.setattr(database, 'SessionLocal', lambda: Session(engine))
    dependency = database.get_db()
    session = next(dependency)
    try:
        original = session.execute(text('SHOW max_parallel_workers_per_gather')).scalar_one()
        pid = session.execute(text('SELECT pg_backend_pid()')).scalar_one()
        apply_read_parallelism(session, 0)
        assert session.execute(text('SHOW max_parallel_workers_per_gather')).scalar_one() == '0'
        if finish == 'commit':
            session.commit()
        elif finish == 'exception':
            with pytest.raises(DBAPIError):
                session.execute(text('SELECT 1 / 0'))
    finally:
        dependency.close()
    try:
        # The same backend is checked out from the one-connection pool.
        with engine.connect() as reused:
            assert reused.execute(text('SELECT pg_backend_pid()')).scalar_one() == pid
            assert reused.execute(text('SHOW max_parallel_workers_per_gather')).scalar_one() == original
    finally:
        engine.dispose()
