from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone
import logging
import uuid
from core.database import SessionLocal
from modules.ingesta.repository.IngestaRepository import IngestaRepository
from modules.jobs.service import enqueue_job
from modules.jobs.worker import process_next_job, recover_abandoned_jobs
from core.config import settings
from shared.export_artifacts import cleanup_expired_artifacts

scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)
logger = logging.getLogger(__name__)

def sincronizar_fuentes_activas():
    print(f"[SCHEDULER] Encolando fuentes vencidas: {datetime.now()}")
    db = SessionLocal()
    try:
        repo = IngestaRepository(db)
        fuentes = repo.get_activas()
        ahora = datetime.now(timezone.utc)

        for fuente in fuentes:
            try:
                # Verificar si ya es tiempo de sincronizar según frecuencia_dias
                if fuente.ultima_sync:
                    dias_transcurridos = (ahora - fuente.ultima_sync).days
                    if dias_transcurridos < fuente.frecuencia_dias:
                        print(
                            f"[SCHEDULER] '{fuente.nombre}' no requiere sync. "
                            f"Faltan {fuente.frecuencia_dias - dias_transcurridos} días."
                        )
                        continue

                job, created = enqueue_job(
                    db,
                    kind="INGESTA",
                    payload={"fuente_id": fuente.id},
                    resource_key=f"ingesta:{fuente.id}",
                )
                print(
                    f"[SCHEDULER] '{fuente.nombre}' "
                    f"{'encolada' if created else 'ya tenía un trabajo activo'} ({job.public_id})"
                )

            except Exception as exc:
                error_id = uuid.uuid4()
                logger.error(
                    "Fallo al encolar sincronización de fuente_id=%s; referencia=%s tipo=%s",
                    fuente.id,
                    error_id,
                    type(exc).__name__,
                )
                continue  # Si falla una fuente, sigue con las demás

    finally:
        db.close()


def iniciar_scheduler():
    if scheduler.running:
        return
    recover_abandoned_jobs()
    cleanup_expired_artifacts()
    scheduler.add_job(
        process_next_job,
        trigger=IntervalTrigger(seconds=2),
        id="process_background_jobs",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        recover_abandoned_jobs,
        trigger=IntervalTrigger(minutes=1),
        id="recover_abandoned_jobs",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        sincronizar_fuentes_activas,
        trigger=IntervalTrigger(hours=24),
        id="sync_fuentes_activas",
        replace_existing=True,
        max_instances=1,  # Evita que se solapen ejecuciones
    )
    scheduler.add_job(
        cleanup_expired_artifacts,
        trigger=IntervalTrigger(hours=1),
        id="cleanup_expired_export_artifacts",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    print("[SCHEDULER] Iniciado. Revisión cada 24 horas.")
