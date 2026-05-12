from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone
from core.database import SessionLocal
from modules.ingesta.repository.IngestaRepository import IngestaRepository
from modules.ingesta.adapters.adapter_factory import get_adapter

scheduler = AsyncIOScheduler(timezone="America/Bogota")

async def sincronizar_fuentes_activas():
    print(f"[SCHEDULER] Iniciando revisión de fuentes: {datetime.now()}")
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

                print(f"[SCHEDULER] Sincronizando '{fuente.nombre}'...")

                adapter = get_adapter(fuente.tipo, fuente.endpoint, fuente.api_key)

                fecha_desde = None
                if fuente.ultima_sync:
                    fecha_desde = fuente.ultima_sync.strftime("%Y-%m-%d")

                total_traidos    = 0
                total_insertados = 0

                for batch in adapter.fetch_todos(fecha_desde=fecha_desde):
                    insertados = repo.insertar_raw_secop_bulk(batch, fuente.id)
                    total_traidos    += len(batch)
                    total_insertados += insertados
                    print(
                        f"[SCHEDULER] '{fuente.nombre}' | "
                        f"traidos={total_traidos} | insertados={total_insertados}"
                    )

                repo.actualizar_ultima_sync(fuente.id, ahora)
                print(
                    f"[SCHEDULER] '{fuente.nombre}' completado. "
                    f"Insertados: {total_insertados}/{total_traidos}"
                )

            except Exception as e:
                print(f"[SCHEDULER ERROR] '{fuente.nombre}': {e}")
                continue  # Si falla una fuente, sigue con las demás

    finally:
        db.close()


def iniciar_scheduler():
    # Revisa cada 12 horas si alguna fuente necesita sync
    # La lógica de frecuencia_dias está dentro del job
    scheduler.add_job(
        sincronizar_fuentes_activas,
        trigger=IntervalTrigger(hours=24),
        id="sync_fuentes_activas",
        replace_existing=True,
        max_instances=1         # Evita que se solapen ejecuciones
    )
    scheduler.start()
    print("[SCHEDULER] Iniciado. Revisión cada 24 horas.")