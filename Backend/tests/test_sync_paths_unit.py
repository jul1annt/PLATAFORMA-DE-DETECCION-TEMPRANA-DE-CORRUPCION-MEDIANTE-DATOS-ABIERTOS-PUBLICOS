from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from core import scheduler
from modules.ingesta.controller import IngestaController


def test_manual_and_scheduled_sync_enqueue_the_same_source_job(monkeypatch):
    source = SimpleNamespace(
        id=73,
        nombre="SECOP test",
        activo=True,
        frecuencia_dias=1,
        ultima_sync=datetime.now(timezone.utc) - timedelta(days=2),
    )
    captured = []

    class Repository:
        def __init__(self, _db):
            pass

        def get_by_id(self, source_id):
            return source if source_id == source.id else None

        def get_activas(self):
            return [source]

    class Database:
        closed = False

        def close(self):
            self.closed = True

    database = Database()

    def capture(_db, **kwargs):
        captured.append(kwargs)
        return SimpleNamespace(public_id="test-job", kind=kwargs["kind"]), True

    monkeypatch.setattr(IngestaController, "IngestaRepository", Repository)
    monkeypatch.setattr(IngestaController, "enqueue_job", capture)
    monkeypatch.setattr(
        IngestaController,
        "to_job_accepted",
        lambda _job: {"id": "test-job"},
    )
    manual = IngestaController.sincronizar_fuente(source.id, db=database)

    monkeypatch.setattr(scheduler, "SessionLocal", lambda: database)
    monkeypatch.setattr(scheduler, "IngestaRepository", Repository)
    monkeypatch.setattr(scheduler, "enqueue_job", capture)
    scheduler.sincronizar_fuentes_activas()

    expected = {
        "kind": "INGESTA",
        "payload": {"fuente_id": source.id},
        "resource_key": f"ingesta:{source.id}",
    }
    assert manual == {"id": "test-job"}
    assert captured == [expected, expected]
    assert database.closed is True
