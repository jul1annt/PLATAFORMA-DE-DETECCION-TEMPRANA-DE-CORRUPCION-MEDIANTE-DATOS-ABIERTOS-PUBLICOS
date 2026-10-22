"""HTTP integration checks for paginated synchronization history endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from core.database import get_db
from gateway.middlewares.auth_middleware import get_current_admin
from main import app
from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.ingesta.model.SincronizacionHistorial import EstadoSync, SincronizacionHistorial
from shared.enums import TipoFormato


@pytest.fixture
def history_client(postgres_test_session):
    def override_db():
        yield postgres_test_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(id=1)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_admin, None)


def _source(session, name: str) -> FuenteDatos:
    source = FuenteDatos(
        nombre=name,
        tipo="SECOP",
        formato=TipoFormato.JSON,
        endpoint=f"https://www.datos.gov.co/resource/{uuid.uuid4().hex[:8]}.json",
    )
    session.add(source)
    session.flush()
    return source


def test_sync_history_page_summary_and_source_filter(history_client, postgres_test_session):
    suffix = uuid.uuid4().hex
    source = _source(postgres_test_session, f"history-{suffix}")
    other_source = _source(postgres_test_session, f"history-other-{suffix}")
    start = datetime.now(timezone.utc)
    logs = [
        SincronizacionHistorial(
            fuente_id=source.id,
            fecha_inicio=start - timedelta(minutes=minutes),
            estado=state,
            mensaje_error=message,
        )
        for minutes, state, message in [
            (1, EstadoSync.EXITOSO, None),
            (2, EstadoSync.ERROR, "fallo sintético"),
            (3, EstadoSync.EN_PROCESO, None),
        ]
    ]
    logs.append(SincronizacionHistorial(
        fuente_id=other_source.id,
        fecha_inicio=start - timedelta(minutes=4),
        estado=EstadoSync.EXITOSO,
    ))
    postgres_test_session.add_all(logs)
    postgres_test_session.flush()

    global_page = history_client.get(
        "/api/ingesta/fuentes/sincronizaciones/pagina",
        params={"page": 2, "size": 2},
    )
    assert global_page.status_code == 200
    assert global_page.json()["total"] == 4
    assert [row["fuente_id"] for row in global_page.json()["items"]] == [source.id, other_source.id]

    source_page = history_client.get(
        f"/api/ingesta/fuentes/{source.id}/sincronizaciones/pagina",
        params={"page": 1, "size": 2},
    )
    assert source_page.status_code == 200
    assert source_page.json()["total"] == 3
    assert [row["estado"] for row in source_page.json()["items"]] == ["EXITOSO", "ERROR"]
    assert source_page.json()["items"][1]["mensaje_error"] == "fallo sintético"

    summary = history_client.get("/api/ingesta/fuentes/sincronizaciones/resumen")
    assert summary.status_code == 200
    assert summary.json() == {
        "total": 4,
        "exitoso": 2,
        "en_proceso": 1,
        "error": 1,
        "parcial": 0,
    }


def test_sync_history_pagination_remains_admin_only(postgres_test_session):
    def override_db():
        yield postgres_test_session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.get("/api/ingesta/fuentes/sincronizaciones/pagina")
        assert response.status_code in (401, 403)
    finally:
        app.dependency_overrides.pop(get_db, None)
