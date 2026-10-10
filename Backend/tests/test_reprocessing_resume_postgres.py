"""Real PostgreSQL disconnects after committed transformation writes."""
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import Session

from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.ingesta.model.RawSecop import RawSecop
from modules.jobs import worker
from modules.jobs.model import BackgroundJob
from modules.jobs.service import enqueue_job
from modules.transformacion.model.ContratoAnomaliaHistorial import ContratoAnomaliaHistorial
from modules.transformacion.model.ContratoAnomaloIncompleto import ContratoAnomaloIncompleto
from modules.transformacion.model.ContratoProcesado import ContratoProcesado
from modules.transformacion.model.ProcesamientoLog import ProcesamientoLog
from modules.transformacion.repository.transformacion import TransformacionRepository
from modules.transformacion.services.trasformacionservice import TransformacionService
from shared.enums import TipoFormato


@pytest.mark.parametrize("failure_point", ["mid_batch", "after_service"])
def test_forced_job_resumes_committed_writes_without_repeating_them(
    postgres_test_session, monkeypatch, failure_point,
):
    engine = create_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    monkeypatch.setattr(worker, "SessionLocal", lambda: Session(engine))
    started, release = Event(), Event()
    observations = {1: [], 2: []}
    job_id = source_id = None
    raw_ids = []
    normalize = TransformacionService._normalizar
    execute = worker._execute
    get_universe = TransformacionRepository.obtener_universo_reprocesamiento
    universe_reads = []

    def observe_universe(repository, forced):
        universe_reads.append(True)
        return get_universe(repository, forced)

    def observe_normalization(service, raw):
        attempt = service.session.get(BackgroundJob, job_id).attempts
        observations[attempt].append(raw.id)
        if failure_point == "mid_batch" and attempt == 1 and len(observations[1]) == 1001:
            observations["pid"] = service.session.execute(text("SELECT pg_backend_pid()")).scalar_one()
            started.set()
            assert release.wait(40)
        return normalize(service, raw)

    def execute_then_pause(kind, payload, **context):
        result = execute(kind, payload, **context)
        db = context["work_db"]
        if failure_point == "after_service" and db.get(BackgroundJob, job_id).attempts == 1:
            observations["pid"] = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
            db.commit()
            started.set()
            assert release.wait(40)
            # Force detection of the disconnect before returning an old result.
            db.execute(text("SELECT 1"))
        return result

    monkeypatch.setattr(TransformacionService, "_normalizar", observe_normalization)
    monkeypatch.setattr(worker, "_execute", execute_then_pause)
    monkeypatch.setattr(TransformacionRepository, "obtener_universo_reprocesamiento", observe_universe)
    try:
        with Session(engine) as db:
            assert db.query(RawSecop).count() == 0
            source = FuenteDatos(nombre=f"resume-{uuid.uuid4()}", tipo="TEST",
                                 formato=TipoFormato.JSON, endpoint="https://example.test/resume")
            db.add(source); db.flush(); source_id = source.id
            rows = [RawSecop(fuente_id=source_id, id_del_proceso=f"resume-{i}")
                    for i in range(2005)]
            db.add_all(rows); db.flush(); raw_ids = [row.id for row in rows]
            db.commit()
            job, _ = enqueue_job(db, kind="REPROCESAMIENTO", payload={"forzar_reproceso": True},
                                 resource_key=f"resume-{uuid.uuid4()}")
            job_id = job.id
        with ThreadPoolExecutor(max_workers=1) as executor:
            original = executor.submit(worker.process_next_job)
            try:
                assert started.wait(40)
                expected_committed = 1000 if failure_point == "mid_batch" else 2005
                with Session(engine) as db:
                    assert db.query(ContratoProcesado).count() == expected_committed
                    first_log = TransformacionRepository(db).obtener_ultimo_log_trabajo(job_id)
                    first_log_id = first_log.id
                    assert first_log.total_evaluados == expected_committed
                    assert first_log.universo["ultimo_raw_secop_id"] == raw_ids[expected_committed - 1]
                    reference_date = first_log.universo["fecha_referencia_anomalias"]
                assert worker.recover_abandoned_jobs() == 0
                with engine.begin() as db:
                    assert db.execute(text("SELECT pg_terminate_backend(:pid, 5000)"),
                                      {"pid": observations["pid"]}).scalar_one()
                assert worker.recover_abandoned_jobs() == 1
                assert worker.process_next_job() is True
            finally:
                release.set()
                assert original.result(timeout=40) is True
        with Session(engine) as db:
            completed = db.get(BackgroundJob, job_id)
            assert completed.status == "EXITOSO" and not completed.active and completed.attempts == 2
            assert completed.result["total_evaluados"] == completed.result["procesados"] == 2005
            assert completed.result["omitidos"] == 0
            assert completed.result["anomalias_registradas"] == 2005 * 5
            assert universe_reads == [True]  # No second full-universe count on recovery.
            assert db.query(ContratoProcesado).count() == 2005
            assert db.query(ContratoAnomaloIncompleto).count() == 2005 * 5
            assert db.query(ContratoAnomaliaHistorial).count() == 0
            logs = db.query(ProcesamientoLog).filter(
                ProcesamientoLog.universo["background_job_id"].as_integer() == job_id,
            ).order_by(ProcesamientoLog.id).all()
            if failure_point == "mid_batch":
                assert observations[2] == raw_ids[1000:]
                assert len(logs) == 2 and logs[0].estado == "ERROR"
                assert logs[0].universo["ultimo_raw_secop_id"] == raw_ids[999]
                assert logs[1].universo["reanudado_desde_log_id"] == first_log_id
                assert logs[1].universo["fecha_referencia_anomalias"] == reference_date
            else:
                assert observations[2] == []
                assert len(logs) == 1
            assert logs[-1].estado == "EXITOSO"
            print("REPROCESSING_RECOVERY_EVIDENCE=" + json.dumps({
                "failure_point": failure_point, "seed_rows": 2005,
                "committed_before_disconnect": expected_committed,
                "second_attempt_normalized_rows": len(observations[2]),
                "second_attempt_repeated_committed_rows": len(
                    set(observations[2]) & set(raw_ids[:expected_committed])),
                "universe_counts_executed": len(universe_reads),
                "final_status": completed.status, "final_attempts": completed.attempts,
                "final_result": completed.result, "active_anomalies": 2005 * 5,
                "archived_anomalies": 0, "reference_date": reference_date,
                "logs": [{"state": log.estado, "universe": log.universo,
                          "evaluated": log.total_evaluados, "processed": log.procesados}
                         for log in logs],
            }))
    finally:
        release.set()
        with Session(engine) as db:
            if raw_ids:
                for model in (ContratoAnomaliaHistorial, ContratoAnomaloIncompleto, ContratoProcesado):
                    db.execute(delete(model).where(model.raw_secop_id.in_(raw_ids)))
                db.execute(delete(RawSecop).where(RawSecop.id.in_(raw_ids)))
            if source_id is not None:
                db.execute(delete(FuenteDatos).where(FuenteDatos.id == source_id))
            if job_id is not None:
                db.execute(delete(ProcesamientoLog).where(
                    ProcesamientoLog.universo["background_job_id"].as_integer() == job_id,
                ))
                db.execute(delete(BackgroundJob).where(BackgroundJob.id == job_id))
            TransformacionRepository(db).recalculate_porcentajes_estadisticas_campos()
            db.commit()
        engine.dispose()
