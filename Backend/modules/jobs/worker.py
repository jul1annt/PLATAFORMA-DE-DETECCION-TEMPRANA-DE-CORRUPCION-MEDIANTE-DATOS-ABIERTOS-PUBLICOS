import json
import logging
import uuid
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import Connection

from core.database import SessionLocal
from modules.jobs.model import BackgroundJob
from shared.export_artifacts import artifact_path


logger = logging.getLogger(__name__)
LOCK_NAMESPACE = 74202
MAX_JOB_ATTEMPTS = 3


class JobConnectionLost(RuntimeError):
    """The executor must stop after losing the PostgreSQL session owning its lock."""


@contextmanager
def _pinned_session():
    """Keep session locks on one physical connection across service commits.

    A Session bound to an Engine returns its connection after each commit.
    An explicitly owned Connection stays checked out until this context ends.
    Reconnecting cannot restore PostgreSQL session locks, so forbid subsequent
    SQL on a replacement connection even if a service catches the disconnect.
    """
    db = SessionLocal()
    connection = None
    owns_connection = False
    fence_reconnection = None
    try:
        bind = db.get_bind()
        owns_connection = not isinstance(bind, Connection)
        connection = bind.connect() if owns_connection else bind
        db.bind = connection
        original = connection.connection.dbapi_connection

        def connection_alive():
            return (
                not connection.closed
                and not connection.invalidated
                and connection.connection.dbapi_connection is original
            )

        def fence_reconnection(conn, _clause, _multiparams, _params, _options):
            if not connection_alive():
                raise JobConnectionLost("Se perdió la conexión que posee el bloqueo del trabajo")

        event.listen(connection, "before_execute", fence_reconnection)
        yield db, connection_alive
    finally:
        try:
            db.close()
        finally:
            if fence_reconnection is not None:
                event.remove(connection, "before_execute", fence_reconnection)
            if connection is not None and owns_connection:
                connection.close()


def IngestaService(db):
    from modules.ingesta.services.IngestaService import IngestaService as implementation
    return implementation(db)


def AnaliticaService(db):
    from modules.analitica.services.AnaliticaService import AnaliticaService as implementation
    return implementation(db)


def TransformacionService(db):
    from modules.transformacion.services.trasformacionservice import TransformacionService as implementation
    return implementation(db)


def generate_contract_export(db, job_public_id, payload):
    from modules.transformacion.services.export_service import generate_contract_export as implementation
    return implementation(db, job_public_id, payload)


def _lock_key(job_id: int) -> int:
    return (LOCK_NAMESPACE << 32) | job_id


def _json_value(value: Any):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.loads(json.dumps(value, default=lambda item: (
        item.isoformat() if isinstance(item, (datetime,)) else
        str(item) if isinstance(item, Decimal) else
        item.value if isinstance(item, Enum) else
        str(item)
    )))


def _execute(
    kind: str, payload: dict, job_public_id=None, job_id: int | None = None,
    work_db=None,
) -> dict:
    with (nullcontext(work_db) if work_db is not None else SessionLocal()) as work_db:
        if kind == "INGESTA":
            result = IngestaService(work_db).sincronizar_fuente(
                int(payload["fuente_id"]), job_id=job_id
            )
        elif kind == "ANALITICA":
            from modules.analitica.dto.request import (
                AdjudicacionDirectaCalculoRequest,
                DuplicadoCalculoRequest,
                OutlierCalculoRequest,
            )
            service = AnaliticaService(work_db)
            tipo = payload["tipo"]
            parametros = dict(payload.get("parametros") or {})
            if tipo == "OUTLIERS":
                result = service.calcular_outliers(
                    OutlierCalculoRequest.model_validate(parametros)
                )
            elif tipo == "DUPLICADOS":
                result = service.calcular_duplicados(
                    DuplicadoCalculoRequest.model_validate(parametros)
                )
            elif tipo == "ADJUDICACION_DIRECTA":
                result = service.calcular_abuso_adjudicacion_directa(
                    AdjudicacionDirectaCalculoRequest.model_validate(parametros)
                )
            elif tipo == "RIESGO":
                result = service.calcular_riesgo_global()
            else:
                raise ValueError(f"Tipo de análisis no soportado: {tipo}")
        elif kind == "REPROCESAMIENTO":
            result = TransformacionService(work_db).process_raw_data(
                forzar_reproceso=bool(payload.get("forzar_reproceso", False)),
                job_id=job_id,
            )
        elif kind == "EXPORTACION_CONTRATOS":
            if job_public_id is None:
                raise ValueError("El trabajo de exportación no tiene identificador público")
            result = generate_contract_export(work_db, job_public_id, payload)
        else:
            raise ValueError(f"Tipo de trabajo no soportado: {kind}")
    return _json_value(result)


def process_next_job() -> bool:
    """Claim and execute one durable job while holding its cross-process lock."""
    with _pinned_session() as (lease_db, connection_alive):
        return _process_next_job(lease_db, connection_alive)


def _process_next_job(lease_db, connection_alive) -> bool:
    job_id = None
    lock_acquired = False
    try:
        job = lease_db.query(BackgroundJob).filter(
            BackgroundJob.status == "PENDIENTE",
            BackgroundJob.active.is_(True),
        ).order_by(BackgroundJob.created_at, BackgroundJob.id).with_for_update(skip_locked=True).first()
        if not job:
            return False

        job_id = job.id
        lock_acquired = bool(lease_db.execute(
            text("SELECT pg_try_advisory_lock(:lock_key)"),
            {"lock_key": _lock_key(job_id)},
        ).scalar())
        if not lock_acquired:
            lease_db.rollback()
            return False

        kind = job.kind
        payload = dict(job.payload)
        job_public_id = job.public_id
        internal_job_id = job.id
        job.status = "EN_PROCESO"
        job.attempts += 1
        job.started_at = datetime.now(timezone.utc)
        job.finished_at = None
        job.error_id = None
        job.error_message = None
        lease_db.commit()

        try:
            result = _execute(
                kind,
                payload,
                job_public_id=job_public_id,
                job_id=internal_job_id,
                work_db=lease_db,
            )
        except Exception as exc:
            lease_db.rollback()
            if not connection_alive():
                # The lock disappeared with the failed connection. Another
                # worker may already have recovered this attempt: do not
                # reconnect and overwrite its status or perform more writes.
                logger.error(
                    "Trabajo %s interrumpido por pérdida de conexión; tipo=%s",
                    job_id, type(exc).__name__,
                )
                return True
            if kind == "EXPORTACION_CONTRATOS" and job_public_id is not None:
                for fmt in ("csv", "xlsx", "pdf"):
                    artifact_path(job_public_id, fmt).unlink(missing_ok=True)
            error_id = uuid.uuid4()
            logger.error(
                "Fallo en trabajo %s, referencia %s, tipo=%s",
                job_id,
                error_id,
                type(exc).__name__,
            )
            job = lease_db.query(BackgroundJob).filter(BackgroundJob.id == job_id).one()
            job.status = "ERROR"
            job.active = False
            job.finished_at = datetime.now(timezone.utc)
            job.error_id = error_id
            job.error_message = f"Error interno. Referencia: {error_id}"
            lease_db.commit()
            return True

        if not connection_alive():
            logger.error("Trabajo %s perdió la conexión antes de guardar su resultado", job_id)
            return True
        job = lease_db.query(BackgroundJob).filter(BackgroundJob.id == job_id).one()
        job.status = "PARCIAL" if result.get("parcial") is True else "EXITOSO"
        job.active = False
        job.finished_at = datetime.now(timezone.utc)
        job.result = result
        lease_db.commit()
        return True
    finally:
        if lock_acquired and job_id is not None and connection_alive():
            try:
                lease_db.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": _lock_key(job_id)},
                )
                lease_db.commit()
            except Exception as exc:
                lease_db.rollback()
                logger.error(
                    "No se pudo liberar el bloqueo del trabajo %s, tipo=%s",
                    job_id,
                    type(exc).__name__,
                )


def recover_abandoned_jobs() -> int:
    """Requeue abandoned jobs with attempts remaining; terminally fail exhausted jobs."""
    with _pinned_session() as (db, _connection_alive):
        return _recover_abandoned_jobs(db)


def _recover_abandoned_jobs(db) -> int:
    recovered = 0
    try:
        job_ids = [row[0] for row in db.query(BackgroundJob.id).filter(
            BackgroundJob.status == "EN_PROCESO",
            BackgroundJob.active.is_(True),
        ).order_by(BackgroundJob.id).all()]
        for job_id in job_ids:
            lock_key = _lock_key(job_id)
            acquired = bool(db.execute(
                text("SELECT pg_try_advisory_lock(:lock_key)"), {"lock_key": lock_key}
            ).scalar())
            if not acquired:
                db.rollback()
                continue
            try:
                job = db.query(BackgroundJob).filter(
                    BackgroundJob.id == job_id,
                    BackgroundJob.status == "EN_PROCESO",
                    BackgroundJob.active.is_(True),
                ).with_for_update(skip_locked=True).first()
                if job:
                    if job.kind == "REPROCESAMIENTO":
                        from modules.transformacion.model.ProcesamientoLog import ProcesamientoLog
                        interrupted = db.query(ProcesamientoLog).filter(
                            ProcesamientoLog.estado == "EN_PROCESO",
                            ProcesamientoLog.universo["background_job_id"].as_integer() == job_id,
                        ).all()
                        for log in interrupted:
                            finished = datetime.now(timezone.utc)
                            log.estado = "ERROR"
                            log.fecha_hora_fin = finished
                            log.duracion_segundos = int((finished - log.fecha_hora_inicio).total_seconds())
                            log.mensaje_error = "Intento interrumpido tras perder el bloqueo del worker"
                    if job.attempts >= MAX_JOB_ATTEMPTS:
                        error_id = uuid.uuid4()
                        job.status = "ERROR"
                        job.active = False
                        job.finished_at = datetime.now(timezone.utc)
                        job.error_id = error_id
                        job.error_message = (
                            f"Se agotaron los {MAX_JOB_ATTEMPTS} intentos tras interrupciones del worker. "
                            f"Referencia: {error_id}"
                        )
                        logger.error(
                            "Trabajo %s agotó %s intentos tras interrupciones, referencia %s",
                            job_id,
                            MAX_JOB_ATTEMPTS,
                            error_id,
                        )
                    else:
                        job.status = "PENDIENTE"
                        job.started_at = None
                        job.error_message = "Trabajo reencolado tras interrupción del worker"
                        recovered += 1
                    db.commit()
                else:
                    db.rollback()
            finally:
                db.execute(text("SELECT pg_advisory_unlock(:lock_key)"), {"lock_key": lock_key})
                db.commit()
    finally:
        db.close()
    return recovered
