"""PostgreSQL coverage for bounded, durable ingestion continuation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from shared.errors import IngestaError

from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.ingesta.model.RawSecop import RawSecop
from modules.ingesta.model.SincronizacionHistorial import EstadoSync, SincronizacionHistorial
from modules.ingesta.services import IngestaService as service_module
from modules.ingesta.services.IngestaService import IngestaService
from modules.jobs.model import BackgroundJob
from shared.enums import TipoFormato


def test_partial_sync_commits_rows_with_cursor_and_next_job_resumes(
    postgres_test_session, monkeypatch
):
    db = postgres_test_session
    source = FuenteDatos(
        nombre=f"cursor-test-{uuid.uuid4().hex[:20]}",
        tipo="SECOP",
        formato=TipoFormato.JSON,
        endpoint="https://www.datos.gov.co/resource/test.json",
        ultima_sync=datetime(2026, 9, 20, 12, tzinfo=timezone.utc),
    )
    db.add(source)
    db.flush()
    resource_key = f"ingesta:{source.id}"
    first_job = BackgroundJob(
        kind="INGESTA",
        payload={"fuente_id": source.id},
        resource_key=resource_key,
        status="EN_PROCESO",
        active=True,
    )
    db.add(first_job)
    db.flush()

    first_batches = [
        [
            {":id": "row-a", "id_del_proceso": "cursor-a"},
            {":id": "row-b", "id_del_proceso": "cursor-b"},
        ],
        [
            {":id": "row-c", "id_del_proceso": "cursor-c"},
            {":id": "row-d", "id_del_proceso": "cursor-d"},
        ],
    ]
    second_batches = [[
        {":id": "row-d", "id_del_proceso": "cursor-d"},
        {":id": "row-e", "id_del_proceso": "cursor-e"},
    ]]
    adapters = [first_batches, RuntimeError("simulated source outage"), second_batches]
    calls = []

    class Adapter:
        def __init__(self, batches):
            self.batches = batches

        def fetch_todos(self, **kwargs):
            calls.append(kwargs)
            if isinstance(self.batches, Exception):
                raise self.batches
            yield from self.batches

    monkeypatch.setattr(service_module.settings, "INGESTA_MAX_RECORDS_PER_SYNC", 3)
    monkeypatch.setattr(
        service_module,
        "get_adapter",
        lambda *_args: Adapter(adapters.pop(0)),
    )

    first_result = IngestaService(db).sincronizar_fuente(source.id, job_id=first_job.id)
    assert first_result["parcial"] is True
    assert first_result["cursor"] == "row-c"
    checkpoint = db.query(BackgroundJob).filter(
        BackgroundJob.id == first_job.id
    ).one().result["checkpoint"]
    assert checkpoint["last_id"] == "row-c"
    assert checkpoint["window_rows"] == 3
    assert db.query(RawSecop).filter(RawSecop.fuente_id == source.id).count() == 3
    assert source.ultima_sync == datetime(2026, 9, 20, 12, tzinfo=timezone.utc)

    first_job.status = "ERROR"
    first_job.active = False
    next_job = BackgroundJob(
        kind="INGESTA",
        payload={"fuente_id": source.id},
        resource_key=resource_key,
        status="EN_PROCESO",
        active=True,
    )
    db.add(next_job)
    db.flush()

    with pytest.raises(IngestaError) as outage:
        IngestaService(db).sincronizar_fuente(source.id, job_id=next_job.id)
    assert outage.value.code == "sync_failed"
    failed_checkpoint = db.query(BackgroundJob).filter(
        BackgroundJob.id == next_job.id
    ).one().result["checkpoint"]
    assert failed_checkpoint["last_id"] == "row-c"
    assert failed_checkpoint["window_from"] == checkpoint["window_from"]
    assert db.query(RawSecop).filter(RawSecop.fuente_id == source.id).count() == 3

    next_job.status = "ERROR"
    next_job.active = False
    resumed_job = BackgroundJob(
        kind="INGESTA",
        payload={"fuente_id": source.id},
        resource_key=resource_key,
        status="EN_PROCESO",
        active=True,
    )
    db.add(resumed_job)
    db.flush()

    second_result = IngestaService(db).sincronizar_fuente(source.id, job_id=resumed_job.id)
    assert second_result["parcial"] is False
    assert second_result["registros_traidos"] == 2
    assert calls[2]["cursor_id"] == "row-c"
    assert calls[2]["fecha_desde"] == calls[0]["fecha_desde"]
    assert calls[2]["fecha_actualizacion_desde"] == calls[0]["fecha_actualizacion_desde"]
    assert calls[2]["fecha_hasta"] == calls[0]["fecha_hasta"]
    assert db.query(RawSecop).filter(RawSecop.fuente_id == source.id).count() == 5
    assert source.ultima_sync == datetime.fromisoformat(first_result["hasta"])
    assert db.query(BackgroundJob).filter(
        BackgroundJob.id == resumed_job.id
    ).one().result["checkpoint"] is None

    history_states = [
        row.estado
        for row in db.query(SincronizacionHistorial)
        .filter(SincronizacionHistorial.fuente_id == source.id)
        .order_by(SincronizacionHistorial.id)
        .all()
    ]
    assert history_states == [EstadoSync.PARCIAL, EstadoSync.ERROR, EstadoSync.EXITOSO]
