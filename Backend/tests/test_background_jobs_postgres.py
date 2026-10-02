import os
import socket
from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from core.database import get_db
from core import scheduler as periodic_scheduler
from main import app
from modules.auth.model.Admin import Admin
from modules.auth.model.AdminSession import AdminSession
from modules.auth.service.AuthService import AuthService
from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.jobs.model import BackgroundJob
from modules.jobs.service import enqueue_job
from modules.jobs import worker as job_worker
from shared.enums import TipoFormato


def test_authenticated_api_enqueues_and_exposes_job_status(postgres_test_session):
    session = postgres_test_session
    admin = Admin(
        username=f"jobs-{uuid.uuid4().hex[:16]}",
        email=f"jobs-{uuid.uuid4().hex[:16]}@example.com",
        hashed_password="unused-test-hash",
        is_active=True,
    )
    session.add(admin)
    session.flush()
    token, jti, expiry = AuthService(session).create_access_token(admin.id, admin.username)
    session.add(AdminSession(jti=jti, admin_id=admin.id, expires_at=expiry))
    source = FuenteDatos(
        nombre=f"jobs-source-{uuid.uuid4().hex[:16]}",
        tipo="SECOP",
        formato=TipoFormato.JSON,
        endpoint="https://www.datos.gov.co/resource/test.json",
        activo=True,
    )
    session.add(source)
    session.flush()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            unauthenticated = client.post(
                "/api/procesados/reprocesar", json={"forzar_reproceso": False}
            )
            assert unauthenticated.status_code == 401

            headers = {"Authorization": f"Bearer {token}"}
            accepted = client.post(
                "/api/procesados/reprocesar",
                json={"forzar_reproceso": False},
                headers=headers,
            )
            assert accepted.status_code == 202
            body = accepted.json()
            assert body["kind"] == "REPROCESAMIENTO"
            assert body["status"] == "PENDIENTE"

            status_response = client.get(f"/api/jobs/{body['id']}", headers=headers)
            assert status_response.status_code == 200
            assert status_response.json()["id"] == body["id"]
            assert status_response.json()["status"] == "PENDIENTE"
            assert client.get(f"/api/jobs/{body['id']}").status_code == 401

            sync_accepted = client.post(
                f"/api/ingesta/fuentes/{source.id}/sincronizar", headers=headers
            )
            assert sync_accepted.status_code == 202
            sync_job_id = sync_accepted.json()["id"]
            duplicate_sync = client.post(
                f"/api/ingesta/fuentes/{source.id}/sincronizar", headers=headers
            )
            assert duplicate_sync.status_code == 202
            assert duplicate_sync.json()["id"] == sync_job_id
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_analytics_calculations_are_durable_background_jobs(postgres_test_session):
    session = postgres_test_session
    admin = Admin(
        username=f"analytics-jobs-{uuid.uuid4().hex[:12]}",
        email=f"analytics-jobs-{uuid.uuid4().hex[:12]}@example.com",
        hashed_password="unused-test-hash",
        is_active=True,
    )
    session.add(admin)
    session.flush()
    token, jti, expiry = AuthService(session).create_access_token(admin.id, admin.username)
    session.add(AdminSession(jti=jti, admin_id=admin.id, expires_at=expiry))

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    headers = {"Authorization": f"Bearer {token}"}
    requests = [
        ("/api/analitica/outliers/calcular", {"campo": "valor_total_normalizado"}, "OUTLIERS"),
        ("/api/analitica/duplicados/calcular", {}, "DUPLICADOS"),
        ("/api/analitica/directas/calcular", {"minimo_directas": 4}, "ADJUDICACION_DIRECTA"),
        ("/api/analitica/riesgo/calcular", {}, "RIESGO"),
    ]
    try:
        with TestClient(app) as client:
            for path, payload, analysis_type in requests:
                response = client.post(path, json=payload, headers=headers)
                assert response.status_code == 202, response.text
                accepted = response.json()
                assert accepted["kind"] == "ANALITICA"
                assert accepted["status"] == "PENDIENTE"
                job = session.query(BackgroundJob).filter_by(
                    public_id=accepted["id"]
                ).one()
                assert job.payload["tipo"] == analysis_type
                assert job.resource_key == f"analitica:{analysis_type}"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_analytic_worker_persists_json_result_in_postgres(postgres_test_session, monkeypatch):
    url = make_url(os.environ["TEST_DATABASE_URL"])
    engine = create_engine(url, pool_size=2, max_overflow=0)
    monkeypatch.setattr(job_worker, "SessionLocal", lambda: Session(engine))

    class Summary(BaseModel):
        total_contratos_analizados: int
        estado_ejecucion: str

    class FakeAnaliticaService:
        def __init__(self, _db):
            pass

        def calcular_outliers(self, request):
            assert request.campo == "valor_total_normalizado"
            return Summary(total_contratos_analizados=17, estado_ejecucion="EXITOSO")

    monkeypatch.setattr(job_worker, "AnaliticaService", FakeAnaliticaService)
    resource = f"analytics-worker:{uuid.uuid4()}"
    job_id = None
    try:
        with Session(engine) as db:
            job, _ = enqueue_job(
                db,
                kind="ANALITICA",
                payload={
                    "tipo": "OUTLIERS",
                    "parametros": {"campo": "valor_total_normalizado"},
                },
                resource_key=resource,
            )
            job_id = job.id

        assert job_worker.process_next_job() is True
        with Session(engine) as db:
            job = db.get(BackgroundJob, job_id)
            assert job.status == "EXITOSO"
            assert job.active is False
            assert job.result == {
                "total_contratos_analizados": 17,
                "estado_ejecucion": "EXITOSO",
            }
    finally:
        if job_id is not None:
            with engine.begin() as db:
                db.execute(delete(BackgroundJob).where(BackgroundJob.id == job_id))
        engine.dispose()


def test_enqueue_is_idempotent_for_active_resource(postgres_test_session):
    resource = f"test-resource:{uuid.uuid4()}"
    first, created_first = enqueue_job(
        postgres_test_session,
        kind="TEST",
        payload={"value": 1},
        resource_key=resource,
    )
    second, created_second = enqueue_job(
        postgres_test_session,
        kind="TEST",
        payload={"value": 2},
        resource_key=resource,
    )
    assert created_first is True
    assert created_second is False
    assert first.public_id == second.public_id


def test_worker_persists_result_and_recovers_orphaned_claim(postgres_test_session, monkeypatch):
    # Use independent connections because a worker commits outside request transactions.
    url = make_url(os.environ["TEST_DATABASE_URL"])
    engine = create_engine(url, pool_size=3, max_overflow=0)
    monkeypatch.setattr(job_worker, "SessionLocal", lambda: Session(engine))

    class FakeIngestaService:
        def __init__(self, db):
            self.db = db

        def sincronizar_fuente(self, fuente_id, job_id=None):
            return {"fuente_id": fuente_id, "registros_traidos": 4}

    class FakeTransformacionService:
        def __init__(self, db):
            self.db = db

        def process_raw_data(self, forzar_reproceso=False):
            return {"forzar_reproceso": forzar_reproceso, "procesados": 2}

    monkeypatch.setattr(job_worker, "IngestaService", FakeIngestaService)
    monkeypatch.setattr(job_worker, "TransformacionService", FakeTransformacionService)
    resource = f"worker-test:{uuid.uuid4()}"
    transform_resource = f"worker-transform-test:{uuid.uuid4()}"
    orphan_resource = f"worker-orphan:{uuid.uuid4()}"
    job_id = None
    transform_job_id = None
    orphan_id = None
    try:
        with Session(engine) as db:
            job, _ = enqueue_job(
                db, kind="INGESTA", payload={"fuente_id": 73}, resource_key=resource
            )
            job_id = job.id
            transform_job, _ = enqueue_job(
                db,
                kind="REPROCESAMIENTO",
                payload={"forzar_reproceso": True},
                resource_key=transform_resource,
            )
            transform_job_id = transform_job.id
            orphan = BackgroundJob(
                kind="TEST",
                payload={"value": 9},
                resource_key=orphan_resource,
                status="EN_PROCESO",
                active=True,
                started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            )
            db.add(orphan)
            db.commit()
            orphan_id = orphan.id

        assert job_worker.process_next_job() is True
        assert job_worker.process_next_job() is True
        with Session(engine) as db:
            completed = db.get(BackgroundJob, job_id)
            assert completed.status == "EXITOSO"
            assert completed.active is False
            assert completed.attempts == 1
            assert completed.result == {"fuente_id": 73, "registros_traidos": 4}
            transformed = db.get(BackgroundJob, transform_job_id)
            assert transformed.status == "EXITOSO"
            assert transformed.result == {"forzar_reproceso": True, "procesados": 2}

        assert job_worker.recover_abandoned_jobs() == 1
        with Session(engine) as db:
            recovered = db.get(BackgroundJob, orphan_id)
            assert recovered.status == "PENDIENTE"
            assert recovered.active is True
            assert "interrupción" in recovered.error_message
    finally:
        with engine.begin() as db:
            if job_id is not None:
                db.execute(delete(BackgroundJob).where(BackgroundJob.id == job_id))
            if transform_job_id is not None:
                db.execute(delete(BackgroundJob).where(BackgroundJob.id == transform_job_id))
            if orphan_id is not None:
                db.execute(delete(BackgroundJob).where(BackgroundJob.id == orphan_id))
        engine.dispose()


def test_abandoned_job_stops_requeueing_after_attempt_limit(postgres_test_session, monkeypatch):
    url = make_url(os.environ["TEST_DATABASE_URL"])
    engine = create_engine(url, pool_size=2, max_overflow=0)
    monkeypatch.setattr(job_worker, "SessionLocal", lambda: Session(engine))
    resource = f"worker-exhausted:{uuid.uuid4()}"
    abandoned_id = None
    replacement_id = None
    try:
        with Session(engine) as db:
            abandoned = BackgroundJob(
                kind="TEST",
                payload={},
                resource_key=resource,
                status="EN_PROCESO",
                active=True,
                attempts=1,
                started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            )
            db.add(abandoned)
            db.commit()
            abandoned_id = abandoned.id

        for attempt in range(1, job_worker.MAX_JOB_ATTEMPTS + 1):
            requeued = job_worker.recover_abandoned_jobs()
            if attempt == job_worker.MAX_JOB_ATTEMPTS:
                assert requeued == 0
                break

            assert requeued == 1
            with Session(engine) as db:
                recovering = db.get(BackgroundJob, abandoned_id)
                assert recovering.status == "PENDIENTE"
                recovering.status = "EN_PROCESO"
                recovering.attempts += 1
                recovering.started_at = datetime.now(timezone.utc)
                db.commit()

        with Session(engine) as db:
            failed = db.get(BackgroundJob, abandoned_id)
            assert failed.status == "ERROR"
            assert failed.active is False
            assert failed.attempts == job_worker.MAX_JOB_ATTEMPTS
            assert failed.finished_at is not None
            assert failed.error_id is not None
            assert "Se agotaron" in failed.error_message

            replacement, created = enqueue_job(
                db, kind="TEST", payload={}, resource_key=resource
            )
            assert created is True
            replacement_id = replacement.id
    finally:
        with engine.begin() as db:
            ids = [job_id for job_id in (abandoned_id, replacement_id) if job_id is not None]
            if ids:
                db.execute(delete(BackgroundJob).where(BackgroundJob.id.in_(ids)))
        engine.dispose()


def test_two_workers_claim_different_jobs_concurrently(postgres_test_session, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, Lock

    url = make_url(os.environ["TEST_DATABASE_URL"])
    engine = create_engine(url, pool_size=4, max_overflow=0)
    monkeypatch.setattr(job_worker, "SessionLocal", lambda: Session(engine))
    both_started = Event()
    guard = Lock()
    executed_values = []
    resources = [f"multi-worker:{uuid.uuid4()}" for _ in range(2)]
    job_ids = []

    def execute(kind, payload, **_context):
        with guard:
            executed_values.append(payload["value"])
            if len(executed_values) == 2:
                both_started.set()
        assert both_started.wait(timeout=10), "el segundo worker no obtuvo otro trabajo"
        return {"value": payload["value"]}

    monkeypatch.setattr(job_worker, "_execute", execute)
    try:
        with Session(engine) as db:
            for value, resource in enumerate(resources, start=3):
                job, _ = enqueue_job(
                    db, kind="TEST", payload={"value": value}, resource_key=resource
                )
                job_ids.append(job.id)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(job_worker.process_next_job) for _ in range(2)]
            assert [future.result(timeout=20) for future in futures] == [True, True]

        assert sorted(executed_values) == [3, 4]
        with Session(engine) as db:
            jobs = [db.get(BackgroundJob, job_id) for job_id in job_ids]
            assert all(job.status == "EXITOSO" and job.attempts == 1 for job in jobs)
    finally:
        with engine.begin() as db:
            if job_ids:
                db.execute(delete(BackgroundJob).where(BackgroundJob.id.in_(job_ids)))
        engine.dispose()


def test_api_remains_responsive_while_secop_request_is_slow(postgres_test_session, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    url = make_url(os.environ["TEST_DATABASE_URL"])
    engine = create_engine(url, pool_size=4, max_overflow=0)
    monkeypatch.setattr(job_worker, "SessionLocal", lambda: Session(engine))
    started = Event()
    release = Event()
    admin_id = None
    session_jti = None
    job_public_id = None
    source_id = None

    class SlowSourceResponse:
        status = 200
        data = b"[]"

        def release_conn(self):
            pass

    def slow_source_request(_pool, method, _url, **_kwargs):
        assert method == "GET"
        started.set()
        assert release.wait(timeout=10), "la fuente HTTP simulada no fue liberada por la prueba"
        return SlowSourceResponse()

    monkeypatch.setattr(
        "modules.ingesta.adapters.secop_adapter.HTTPSConnectionPool.urlopen",
        slow_source_request,
    )
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 443))
    ])

    with Session(engine) as db:
        suffix = uuid.uuid4().hex
        admin = Admin(
            username=f"slow-job-{suffix[:16]}",
            email=f"slow-job-{suffix}@example.test",
            hashed_password="unused-test-hash",
            is_active=True,
        )
        db.add(admin)
        db.flush()
        token, session_jti, expiry = AuthService(db).create_access_token(admin.id, admin.username)
        db.add(AdminSession(jti=session_jti, admin_id=admin.id, expires_at=expiry))
        source = FuenteDatos(
            nombre=f"slow-source-{suffix[:16]}",
            tipo="SECOP",
            formato=TipoFormato.JSON,
            endpoint="https://www.datos.gov.co/resource/test.json",
            activo=True,
        )
        db.add(source)
        db.commit()
        admin_id = admin.id
        source_id = source.id

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with TestClient(app) as client:
            accepted = client.post(
                f"/api/ingesta/fuentes/{source_id}/sincronizar",
                headers=headers,
            )
            assert accepted.status_code == 202
            job_public_id = accepted.json()["id"]

            with ThreadPoolExecutor(max_workers=1) as executor:
                worker_result = executor.submit(job_worker.process_next_job)
                assert started.wait(timeout=5), "el worker no empezó el trabajo"
                running = client.get(f"/api/jobs/{job_public_id}", headers=headers)
                assert running.status_code == 200
                assert running.json()["status"] == "EN_PROCESO"
                release.set()
                assert worker_result.result(timeout=5) is True

            completed = client.get(f"/api/jobs/{job_public_id}", headers=headers)
            assert completed.status_code == 200
            assert completed.json()["status"] == "EXITOSO"
            assert completed.json()["result"]["registros_traidos"] == 0
    finally:
        release.set()
        app.dependency_overrides.pop(get_db, None)
        with engine.begin() as db:
            if job_public_id is not None:
                db.execute(delete(BackgroundJob).where(BackgroundJob.public_id == job_public_id))
            if session_jti is not None:
                db.execute(delete(AdminSession).where(AdminSession.jti == session_jti))
            if source_id is not None:
                from modules.ingesta.model.SincronizacionHistorial import SincronizacionHistorial

                db.execute(delete(SincronizacionHistorial).where(
                    SincronizacionHistorial.fuente_id == source_id
                ))
                db.execute(delete(FuenteDatos).where(FuenteDatos.id == source_id))
            if admin_id is not None:
                db.execute(delete(Admin).where(Admin.id == admin_id))
        engine.dispose()


def test_periodic_scheduler_enqueues_due_source_without_running_ingestion(
    postgres_test_session, monkeypatch
):
    url = make_url(os.environ["TEST_DATABASE_URL"])
    engine = create_engine(url, pool_size=2, max_overflow=0)
    monkeypatch.setattr(periodic_scheduler, "SessionLocal", lambda: Session(engine))
    source_id = None
    job_id = None
    source_name = f"scheduler-test-{uuid.uuid4().hex[:16]}"
    try:
        with Session(engine) as db:
            source = FuenteDatos(
                nombre=source_name,
                tipo="SECOP",
                formato=TipoFormato.JSON,
                endpoint="https://www.datos.gov.co/resource/test.json",
                activo=True,
                frecuencia_dias=1,
            )
            db.add(source)
            db.commit()
            source_id = source.id

        periodic_scheduler.sincronizar_fuentes_activas()

        with Session(engine) as db:
            job = db.query(BackgroundJob).filter(
                BackgroundJob.resource_key == f"ingesta:{source_id}",
                BackgroundJob.active.is_(True),
            ).one()
            assert job.kind == "INGESTA"
            assert job.status == "PENDIENTE"
            assert job.payload == {"fuente_id": source_id}
            job_id = job.id
    finally:
        with engine.begin() as db:
            if job_id is not None:
                db.execute(delete(BackgroundJob).where(BackgroundJob.id == job_id))
            if source_id is not None:
                db.execute(delete(FuenteDatos).where(FuenteDatos.id == source_id))
        engine.dispose()
