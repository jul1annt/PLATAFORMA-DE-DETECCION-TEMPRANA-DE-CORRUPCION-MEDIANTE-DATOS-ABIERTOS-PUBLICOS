from datetime import datetime, timezone
import os
from types import SimpleNamespace
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi.testclient import TestClient

from core.database import get_db
from main import app
from modules.jobs import exports_controller
from modules.jobs import worker
from modules.transformacion.controller import transformacionController
from modules.transformacion.services import export_service
from shared.export_artifacts import (
    artifact_path,
    cleanup_expired_artifacts,
    create_export_token,
    parse_export_token,
    result_artifact_path,
    write_artifact,
)


client = TestClient(app)
JOB_ID = UUID("6fb4f936-708f-4c28-bdc3-8f87d5086fa3")


def test_late_export_attempt_cannot_overwrite_recovered_artifact(tmp_path, monkeypatch):
    started, release = Event(), Event()

    class Repository:
        def __init__(self, _db):
            pass

        def search_contratos(self, _filters, **_kwargs):
            return [], 0

    def render(*_args):
        if not started.is_set():
            started.set()
            assert release.wait(10)
            return SimpleNamespace(body=b"stale attempt", media_type="text/csv")
        return SimpleNamespace(body=b"recovered attempt", media_type="text/csv")

    monkeypatch.setattr(export_service, "TransformacionRepository", Repository)
    monkeypatch.setattr(export_service, "render_export", render)
    monkeypatch.setattr("shared.export_artifacts.settings.EXPORT_ARTIFACT_DIR", str(tmp_path))
    payload = {"format": "csv", "filters": {}, "expires_at": 2_000_000_000}
    with ThreadPoolExecutor(max_workers=1) as executor:
        old = executor.submit(export_service.generate_contract_export, object(), JOB_ID, payload)
        try:
            assert started.wait(10)
            recovered = export_service.generate_contract_export(object(), JOB_ID, payload)
        finally:
            release.set()
            stale = old.result(timeout=10)
    # Results without artifact_id represent the former stable filename.
    artifact = artifact_path(UUID(recovered.get("artifact_id", str(JOB_ID))), "csv")
    assert artifact.read_bytes() == b"recovered attempt"
    assert stale.get("artifact_id") != recovered.get("artifact_id")


class _Query:
    def __init__(self, job):
        self.job = job

    def filter(self, *_args):
        return self

    def first(self):
        return self.job


class _Database:
    def __init__(self, job=None):
        self.job = job

    def query(self, *_args):
        return _Query(self.job)


def test_export_capability_token_is_bound_to_job_and_tamper_evident():
    token = create_export_token(JOB_ID, 2_000_000_000)

    assert parse_export_token(JOB_ID, token) == 2_000_000_000
    assert parse_export_token(UUID(int=JOB_ID.int + 1), token) is None
    assert parse_export_token(JOB_ID, token + "x") is None
    assert parse_export_token(JOB_ID, None) is None


def test_artifact_write_is_atomic_and_uses_server_generated_name(tmp_path):
    path, checksum = write_artifact(JOB_ID, "csv", b"safe export", directory=tmp_path)

    assert path == tmp_path.resolve() / f"{JOB_ID}.csv"
    assert path.read_bytes() == b"safe export"
    assert len(checksum) == 64
    assert not list(tmp_path.glob("*.tmp"))
    with pytest.raises(ValueError):
        artifact_path(JOB_ID, "../../secret", directory=tmp_path)


@pytest.mark.parametrize("invalid_id", ["../secret", "C:/secret.csv", None, {}])
def test_artifact_result_rejects_paths_instead_of_server_identifiers(tmp_path, invalid_id):
    with pytest.raises(ValueError):
        result_artifact_path(JOB_ID, {"format": "csv", "artifact_id": invalid_id},
                             directory=tmp_path)


def test_expired_artifact_cleanup_removes_only_old_export_files(tmp_path, monkeypatch):
    monkeypatch.setattr("shared.export_artifacts.settings.EXPORT_ARTIFACT_TTL_HOURS", 1)
    expired = tmp_path / f"{JOB_ID}.csv"
    recent = tmp_path / f"{UUID(int=JOB_ID.int + 1)}.xlsx"
    unrelated = tmp_path / "notes.txt"
    expired.write_bytes(b"old")
    recent.write_bytes(b"new")
    unrelated.write_bytes(b"keep")
    os.utime(expired, (100, 100))
    os.utime(recent, (9900, 9900))

    assert cleanup_expired_artifacts(now=10000, directory=tmp_path) == 1
    assert not expired.exists()
    assert recent.exists()
    assert unrelated.exists()


def test_export_job_creation_stores_canonical_filters_and_signed_expiry(monkeypatch):
    job = SimpleNamespace(public_id=JOB_ID, status="PENDIENTE")
    saved = {}

    class Repository:
        def __init__(self, _db):
            pass

        def search_contratos(self, filters, **kwargs):
            saved["filters"] = filters
            saved["count_query"] = kwargs
            return [object()], 15000

    def fake_enqueue(_db, **kwargs):
        saved["job"] = kwargs
        return job, True

    monkeypatch.setattr(transformacionController, "TransformacionRepository", Repository)
    monkeypatch.setattr(transformacionController, "enqueue_job", fake_enqueue)
    app.dependency_overrides[get_db] = lambda: object()
    try:
        response = client.post(
            "/api/procesados/export/xlsx/jobs?q=acme&sort=fecha&order=asc&limit=25&offset=50"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 202
    body = response.json()
    assert body["id"] == str(JOB_ID)
    assert body["status_url"] == f"/api/exports/{JOB_ID}"
    assert body["download_url"] == f"/api/exports/{JOB_ID}/download"
    expires_at = int(datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00")).timestamp())
    assert parse_export_token(JOB_ID, body["access_token"]) == expires_at
    assert saved["filters"].query == "acme"
    assert saved["count_query"]["limit"] == 1
    assert saved["job"]["kind"] == "EXPORTACION_CONTRATOS"
    assert saved["job"]["payload"]["format"] == "xlsx"
    assert saved["job"]["payload"]["filters"]["query"] == "acme"
    assert "token=" not in body["status_url"]


def test_export_job_creation_enforces_configured_volume_limit(monkeypatch):
    monkeypatch.setattr("modules.transformacion.controller.transformacionController.settings.EXPORT_MAX_ROWS", 10)

    class Repository:
        def __init__(self, _db):
            pass

        def search_contratos(self, _filters, **_kwargs):
            return [object()], 11

    def unexpected_enqueue(*_args, **_kwargs):
        raise AssertionError("No se debe encolar una exportación sobre el límite")

    monkeypatch.setattr(transformacionController, "TransformacionRepository", Repository)
    monkeypatch.setattr(transformacionController, "enqueue_job", unexpected_enqueue)
    app.dependency_overrides[get_db] = lambda: object()
    try:
        response = client.post("/api/procesados/export/csv/jobs")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 413


@pytest.mark.parametrize("per_attempt", [False, True])
def test_export_status_requires_capability_and_downloads_expiring_file(tmp_path, monkeypatch, per_attempt):
    expires_at = 2_000_000_000
    token = create_export_token(JOB_ID, expires_at)
    job = SimpleNamespace(
        public_id=JOB_ID,
        kind="EXPORTACION_CONTRATOS",
        payload={"expires_at": expires_at},
        status="EXITOSO",
        created_at=datetime.now(timezone.utc),
        result={"format": "csv", "filename": "contratos_calidad.csv", "media_type": "text/csv"},
        error_message=None,
    )
    monkeypatch.setattr("shared.export_artifacts.settings.EXPORT_ARTIFACT_DIR", str(tmp_path))
    artifact_id = UUID(int=JOB_ID.int + 1) if per_attempt else JOB_ID
    if per_attempt:
        job.result["artifact_id"] = str(artifact_id)
        write_artifact(JOB_ID, "csv", b"wrong legacy content")
    write_artifact(artifact_id, "csv", b"id;entidad\n1;Contrataci\xc3\xb3n\n")
    app.dependency_overrides[get_db] = lambda: _Database(job)
    try:
        invalid = client.get(f"/api/exports/{JOB_ID}", headers={"X-Export-Token": token + "x"})
        status_response = client.get(f"/api/exports/{JOB_ID}", headers={"X-Export-Token": token})
        download = client.get(
            f"/api/exports/{JOB_ID}/download",
            headers={"X-Export-Token": token},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert invalid.status_code == 404
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "EXITOSO"
    assert download.status_code == 200
    assert download.content.startswith(b"id;entidad")
    assert download.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("per_attempt", [False, True])
def test_expired_export_capability_removes_artifact_and_returns_gone(tmp_path, monkeypatch, per_attempt):
    monkeypatch.setattr("shared.export_artifacts.settings.EXPORT_ARTIFACT_DIR", str(tmp_path))
    artifact_id = UUID(int=JOB_ID.int + 1) if per_attempt else JOB_ID
    path, _ = write_artifact(artifact_id, "csv", b"expired")
    job = SimpleNamespace(kind="EXPORTACION_CONTRATOS", payload={"expires_at": 1},
                          result={"format": "csv", "artifact_id": str(artifact_id)})
    expired_token = create_export_token(JOB_ID, 1)
    app.dependency_overrides[get_db] = lambda: _Database(job if per_attempt else None)
    try:
        response = client.get(
            f"/api/exports/{JOB_ID}/download",
            headers={"X-Export-Token": expired_token},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 410
    assert not path.exists()


def test_export_worker_generates_bounded_artifact_and_metadata(tmp_path, monkeypatch):
    item = SimpleNamespace(
        id=1,
        entidad_normalizada="=formula",
        proveedor_normalizado="proveedor",
        modalidad_contratacion="directa",
        valor_total_normalizado=100,
        fecha_publicacion_normalizada=None,
        estado_normalizado="cerrado",
        nivel_confianza=80,
        es_incompleto=False,
        es_sospechoso=False,
        clasificacion_riesgo="SIN_EVALUAR",
    )

    class Repository:
        def __init__(self, _db):
            pass

        def search_contratos(self, _filters, **kwargs):
            assert kwargs["limit"] == 50001
            return [item], 1

    class SessionContext:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr("modules.transformacion.services.export_service.TransformacionRepository", Repository)
    monkeypatch.setattr("shared.export_artifacts.settings.EXPORT_ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setattr(worker, "SessionLocal", SessionContext)
    result = worker._execute(
        "EXPORTACION_CONTRATOS",
        {
            "format": "csv",
            "filters": {},
            "sort": None,
            "order": "desc",
            "expires_at": 2_000_000_000,
        },
        job_public_id=JOB_ID,
    )

    artifact = result_artifact_path(JOB_ID, result, directory=tmp_path)
    assert result["row_count"] == 1
    assert result["sha256"]
    assert artifact.is_file()
    assert b"'=formula" in artifact.read_bytes()


def test_worker_rechecks_volume_and_does_not_publish_over_limit(tmp_path, monkeypatch):
    class Repository:
        def __init__(self, _db):
            pass

        def search_contratos(self, _filters, **kwargs):
            assert kwargs["limit"] == 4
            # New records can match after the request-time count.
            return [object(), object(), object(), object()], 4

    monkeypatch.setattr(export_service, "TransformacionRepository", Repository)
    monkeypatch.setattr(export_service.settings, "EXPORT_MAX_ROWS", 3)
    monkeypatch.setattr("shared.export_artifacts.settings.EXPORT_ARTIFACT_DIR", str(tmp_path))

    with pytest.raises(export_service.ExportLimitExceededError):
        export_service.generate_contract_export(
            object(),
            JOB_ID,
            {"format": "csv", "filters": {}, "expires_at": 2_000_000_000},
        )

    assert not artifact_path(JOB_ID, "csv", directory=tmp_path).exists()
