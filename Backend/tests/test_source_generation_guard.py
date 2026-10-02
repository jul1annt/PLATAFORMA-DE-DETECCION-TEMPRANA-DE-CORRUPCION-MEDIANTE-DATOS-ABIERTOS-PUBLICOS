from datetime import datetime, timezone
from types import SimpleNamespace

from modules.ingesta.adapters.secop_adapter import SecopAdapter
from modules.ingesta.model.SincronizacionHistorial import EstadoSync
from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.ingesta.repository.IngestaRepository import IngestaRepository
from modules.ingesta.services import IngestaService as service_module
from modules.ingesta.services.IngestaService import IngestaService
from shared.enums import TipoFormato


def test_generation_probe_checks_ids_outside_the_sync_watermark():
    adapter = SecopAdapter.__new__(SecopAdapter)
    adapter.api_key = None
    requests = []
    adapter.close = lambda: None

    def request(_headers, params):
        requests.append(params)
        if "$where" in params:
            return [{":id": "row-present"}]
        return [{"filas": "9249545", "min_actualizacion": "2026-10-01T17:30:18.584Z",
                 "max_actualizacion": "2026-10-01T17:30:18.584Z"}]

    adapter._request_json = request
    result = adapter.probe_generation(["row-present", "row-gone"])

    assert result["filas"] == 9_249_545
    assert result["sample_missing"] == 1
    assert ":updated_at" in requests[0]["$select"]
    assert ":id in" in requests[1]["$where"]
    assert "fecha_de_publicacion_del" not in requests[1]["$where"]


def test_replacement_stops_sync_without_fetching_or_advancing_watermark(monkeypatch):
    class Repository:
        closed = None
        checkpoint_cleared = False
        watermark_advanced = False
        lock_released = False
        source_paused = False

        def get_by_id(self, _source_id):
            return SimpleNamespace(
                id=1, nombre="SECOP II", tipo="SECOP", endpoint="https://www.datos.gov.co/resource/p6dx-8zbt.json",
                api_key=None, ultima_sync=datetime(2026, 9, 29, tzinfo=timezone.utc),
            )

        def try_sync_lock(self, _source_id):
            return True

        def crear_historial(self, _source_id):
            return SimpleNamespace(id=10)

        def get_sync_checkpoint(self, _source_id, _job_id):
            return None

        def local_generation_sample(self, _source_id):
            return True, [f"old-{index}" for index in range(10)]

        def clear_sync_checkpoint(self, _source_id, _job_id):
            self.checkpoint_cleared = True

        def suspend_source_for_reconciliation(self, _source_id):
            self.source_paused = True

        def cerrar_historial(self, _id, fetched, inserted, status, error=None):
            self.closed = (fetched, inserted, status, error)

        def actualizar_ultima_sync(self, *_args, **_kwargs):
            self.watermark_advanced = True

        def release_sync_lock(self, _source_id):
            self.lock_released = True

    class Adapter:
        def probe_generation(self, row_ids):
            assert len(row_ids) == 10
            return {"filas": 9_249_545, "min_actualizacion": "2026-10-01T17:30:18.584Z",
                    "max_actualizacion": "2026-10-01T17:30:18.584Z",
                    "sample_checked": 10, "sample_missing": 10}

        def fetch_todos(self, **_kwargs):
            raise AssertionError("A changed generation must not enter the normal sync loop")

    repository = Repository()
    service = IngestaService(None)
    service.repo = repository
    monkeypatch.setattr(service_module, "get_adapter", lambda *_args: Adapter())

    result = service.sincronizar_fuente(1, job_id=81)

    assert result["parcial"] is True
    assert result["replacement_detected"] is True
    assert result["checkpoint"] is None
    assert result["source_paused"] is True
    assert repository.closed[0:3] == (0, 0, EstadoSync.PARCIAL)
    assert repository.checkpoint_cleared is True
    assert repository.watermark_advanced is False
    assert repository.source_paused is True
    assert repository.lock_released is True


def test_suspended_source_is_excluded_from_scheduled_sources(postgres_test_session):
    source = FuenteDatos(
        nombre="SECOP generation guard test",
        tipo="SECOP",
        formato=TipoFormato.JSON,
        endpoint="https://www.datos.gov.co/resource/p6dx-8zbt.json",
        frecuencia_dias=1,
        activo=True,
    )
    postgres_test_session.add(source)
    postgres_test_session.flush()
    repo = IngestaRepository(postgres_test_session)

    assert source.id in {item.id for item in repo.get_activas()}
    repo.suspend_source_for_reconciliation(source.id)

    assert repo.get_by_id(source.id).activo is False
    assert source.id not in {item.id for item in repo.get_activas()}
