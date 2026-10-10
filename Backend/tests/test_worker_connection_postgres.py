"""Regression checks for connection ownership across worker commits and failures."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from datetime import datetime, timezone

from sqlalchemy import create_engine, delete, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError
import pytest

from modules.jobs import worker
from modules.jobs.model import BackgroundJob
from modules.jobs.service import enqueue_job
from modules.transformacion.model.ProcesamientoLog import ProcesamientoLog


def test_worker_keeps_lock_connection_checked_out_between_commits(
    postgres_test_session, monkeypatch,
):
    url = make_url(os.environ['TEST_DATABASE_URL'])
    engine = create_engine(url, pool_size=2, max_overflow=0)
    monkeypatch.setattr(worker, 'SessionLocal', lambda: Session(engine))
    started, release = Event(), Event()
    job_id = None

    def execute(_kind, _payload, **_context):
        started.set()
        assert release.wait(15)
        return {'done': True}

    monkeypatch.setattr(worker, '_execute', execute)
    try:
        with Session(engine) as db:
            job, _ = enqueue_job(db, kind='TEST', payload={},
                                 resource_key=f'connection-regression:{uuid.uuid4()}')
            job_id = job.id
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(worker.process_next_job)
            try:
                assert started.wait(10)
                # A service may be waiting for HTTP between committed batches.
                # Its session-level lock must not be borrowed by the recovery loop.
                assert worker.recover_abandoned_jobs() == 0
                assert engine.pool.checkedout() == 1
                with Session(engine) as db:
                    assert db.get(BackgroundJob, job_id).status == 'EN_PROCESO'
            finally:
                release.set()
                assert future.result(timeout=10) is True
        assert engine.pool.checkedout() == 0
        with Session(engine) as db:
            assert db.get(BackgroundJob, job_id).status == 'EXITOSO'
    finally:
        release.set()
        if job_id is not None:
            with engine.begin() as db:
                db.execute(delete(BackgroundJob).where(BackgroundJob.id == job_id))
        engine.dispose()


def test_disconnected_attempt_cannot_reconnect_and_overwrite_recovered_job(
    postgres_test_session, monkeypatch,
):
    url = make_url(os.environ['TEST_DATABASE_URL'])
    engine = create_engine(url, pool_size=4, max_overflow=0, pool_pre_ping=True)
    monkeypatch.setattr(worker, 'SessionLocal', lambda: Session(engine))
    started, release = Event(), Event()
    observations = {}
    job_id = None

    class InterruptedIngestion:
        def __init__(self, db):
            self.db = db

        def sincronizar_fuente(self, _source_id, job_id=None):
            attempt = self.db.get(BackgroundJob, job_id).attempts
            if attempt == 2:
                return {'owner': 'recovered', 'attempt': attempt}
            observations['pid'] = self.db.execute(text('SELECT pg_backend_pid()')).scalar_one()
            self.db.commit()
            started.set()
            assert release.wait(15)
            # Observe an actual dropped PostgreSQL connection, then emulate a
            # service attempting to recover internally after rolling back.
            with pytest.raises(DBAPIError):
                self.db.execute(text('SELECT 1'))
            self.db.rollback()
            with pytest.raises(worker.JobConnectionLost):
                self.db.execute(text(
                    'UPDATE background_jobs SET status=\'ERROR\' WHERE id=:id'
                ), {'id': job_id})
            observations['stale_write_blocked'] = True
            return {'owner': 'stale'}

    monkeypatch.setattr(worker, 'IngestaService', InterruptedIngestion)
    try:
        with Session(engine) as db:
            job, _ = enqueue_job(db, kind='INGESTA', payload={'fuente_id': 1},
                                 resource_key=f'disconnect-regression:{uuid.uuid4()}')
            job_id = job.id
        with ThreadPoolExecutor(max_workers=1) as executor:
            original = executor.submit(worker.process_next_job)
            try:
                assert started.wait(10)
                with engine.begin() as db:
                    assert db.execute(text('SELECT pg_terminate_backend(:pid)'),
                                      {'pid': observations['pid']}).scalar_one()
                assert worker.recover_abandoned_jobs() == 1
                assert worker.process_next_job() is True
            finally:
                release.set()
                assert original.result(timeout=10) is True
        assert observations['stale_write_blocked'] is True
        with Session(engine) as db:
            recovered = db.get(BackgroundJob, job_id)
            assert recovered.status == 'EXITOSO'
            assert recovered.attempts == 2
            assert recovered.result == {'owner': 'recovered', 'attempt': 2}
        assert engine.pool.checkedout() == 0
    finally:
        release.set()
        if job_id is not None:
            with engine.begin() as db:
                db.execute(delete(BackgroundJob).where(BackgroundJob.id == job_id))
        engine.dispose()


def test_recovery_closes_only_processing_logs_linked_to_the_abandoned_job(
    postgres_test_session, monkeypatch,
):
    url = make_url(os.environ['TEST_DATABASE_URL'])
    engine = create_engine(url)
    monkeypatch.setattr(worker, 'SessionLocal', lambda: Session(engine))
    job_id, log_ids = None, []
    try:
        with Session(engine) as db:
            job = BackgroundJob(kind='REPROCESAMIENTO', payload={},
                                resource_key=f'log-recovery:{uuid.uuid4()}',
                                status='EN_PROCESO', active=True, attempts=1)
            db.add(job); db.flush(); job_id = job.id
            scopes = [
                {'background_job_id': job_id, 'ultimo_raw_secop_id': 1000},
                {'background_job_id': job_id + 1000000},
                {},
            ]
            for scope in scopes:
                log = ProcesamientoLog(estado='EN_PROCESO', universo=scope,
                                       version_reglas='v1.0',
                                       fecha_hora_inicio=datetime.now(timezone.utc))
                db.add(log); db.flush(); log_ids.append(log.id)
            db.commit()
        assert worker.recover_abandoned_jobs() == 1
        with Session(engine) as db:
            interrupted = db.get(ProcesamientoLog, log_ids[0])
            assert interrupted.estado == 'ERROR'
            assert interrupted.fecha_hora_fin is not None
            assert interrupted.universo['ultimo_raw_secop_id'] == 1000
            assert db.get(ProcesamientoLog, log_ids[1]).estado == 'EN_PROCESO'
            assert db.get(ProcesamientoLog, log_ids[2]).estado == 'EN_PROCESO'
            assert db.get(BackgroundJob, job_id).status == 'PENDIENTE'
    finally:
        with engine.begin() as db:
            if log_ids:
                db.execute(delete(ProcesamientoLog).where(ProcesamientoLog.id.in_(log_ids)))
            if job_id is not None:
                db.execute(delete(BackgroundJob).where(BackgroundJob.id == job_id))
        engine.dispose()


def test_executor_uses_the_connection_that_owns_the_job_lock(
    postgres_test_session, monkeypatch,
):
    url = make_url(os.environ['TEST_DATABASE_URL'])
    engine = create_engine(url, pool_size=2, max_overflow=0)
    monkeypatch.setattr(worker, 'SessionLocal', lambda: Session(engine))
    job_id = None
    observations = []

    class InspectIngestion:
        def __init__(self, db):
            self.db = db

        def sincronizar_fuente(self, _source_id, job_id=None):
            for _ in range(3):
                pid = self.db.execute(text('SELECT pg_backend_pid()')).scalar_one()
                locked = self.db.execute(text(
                    'SELECT count(*) FROM pg_locks WHERE pid=pg_backend_pid() '
                    "AND locktype='advisory' AND classid=:namespace AND objid=:job_id"
                ), {'namespace': worker.LOCK_NAMESPACE, 'job_id': job_id}).scalar_one()
                observations.append((pid, locked))
                self.db.commit()
            return {'observations': len(observations)}

    monkeypatch.setattr(worker, 'IngestaService', InspectIngestion)
    try:
        with Session(engine) as db:
            job, _ = enqueue_job(db, kind='INGESTA', payload={'fuente_id': 1},
                                 resource_key=f'executor-connection:{uuid.uuid4()}')
            job_id = job.id
        assert worker.process_next_job() is True
        assert len(observations) == 3
        assert len({pid for pid, _locked in observations}) == 1
        assert all(locked == 1 for _pid, locked in observations)
        assert engine.pool.checkedout() == 0
    finally:
        if job_id is not None:
            with engine.begin() as db:
                db.execute(delete(BackgroundJob).where(BackgroundJob.id == job_id))
        engine.dispose()
