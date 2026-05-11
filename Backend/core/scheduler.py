from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone
from core.database import SessionLocal
from modules.ingesta.repository.IngestaRepository import IngestaRepository
from modules.ingesta.adapters.adapter_factory import get_adapter

scheduler = AsyncIOScheduler()

async def sincronizar_fuentes_activas():
    db = SessionLocal()
    try:
        repo = IngestaRepository(db)
        fuentes = repo.get_activas()
        ahora = datetime.now(timezone.utc)

        for fuente in fuentes:
            # Verifica si ya es tiempo de sincronizar
            if fuente.ultima_sync:
                dias_transcurridos = (ahora - fuente.ultima_sync).days
                if dias_transcurridos < fuente.frecuencia_dias:
                    continue
            try:
                adapter = get_adapter(fuente.tipo, fuente.api_key)
                datos = adapter.fetch()
                # Persistir datos crudos (próxima HU)
                repo.actualizar_ultima_sync(fuente.id, ahora)
                print(f"[SYNC OK] {fuente.nombre}: {len(datos)} registros")
            except Exception as e:
                print(f"[SYNC ERROR] {fuente.nombre}: {e}")
    finally:
        db.close()

def iniciar_scheduler():
    scheduler.add_job(
        sincronizar_fuentes_activas,
        trigger=IntervalTrigger(hours=12),  # Revisa cada 12h, la lógica de días está en el job
        id="sync_fuentes",
        replace_existing=True
    )
    scheduler.start()