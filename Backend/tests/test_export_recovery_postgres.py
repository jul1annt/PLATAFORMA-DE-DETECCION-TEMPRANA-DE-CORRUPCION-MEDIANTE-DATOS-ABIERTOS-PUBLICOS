"""A late renderer must not replace the artifact of a recovered durable job."""
import hashlib
import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import Session

from core.database import get_db
from main import app
from modules.jobs import worker
from modules.jobs.model import BackgroundJob
from modules.jobs.service import enqueue_job
from modules.transformacion.services import export_service
from shared.export_artifacts import cleanup_expired_artifacts, create_export_token, result_artifact_path


def test_recovered_export_remains_downloadable_after_late_renderer_finishes(
    postgres_test_session, monkeypatch, tmp_path,
):
    engine = create_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    monkeypatch.setattr(worker, "SessionLocal", lambda: Session(engine))
    monkeypatch.setattr("shared.export_artifacts.settings.EXPORT_ARTIFACT_DIR", str(tmp_path))
    started, release = Event(), Event()
    observed = {}
    job_id = public_id = None
    generate = worker.generate_contract_export
    expiry = 2_000_000_000

    def generate_and_observe(db, public, payload):
        if db.get(BackgroundJob, job_id).attempts == 1:
            observed["pid"] = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
        return generate(db, public, payload)

    def paused_render(*_args):
        if not started.is_set():
            started.set()
            assert release.wait(30)
            return SimpleNamespace(body=b"stale attempt", media_type="text/csv")
        return SimpleNamespace(body=b"recovered attempt", media_type="text/csv")

    def database():
        with Session(engine) as db:
            yield db

    monkeypatch.setattr(worker, "generate_contract_export", generate_and_observe)
    monkeypatch.setattr(export_service, "render_export", paused_render)
    try:
        with Session(engine) as db:
            job, _ = enqueue_job(db, kind="EXPORTACION_CONTRATOS",
                                 payload={"format": "csv", "filters": {}, "expires_at": expiry},
                                 resource_key=f"export-recovery:{uuid.uuid4()}")
            job_id, public_id = job.id, job.public_id
        with ThreadPoolExecutor(max_workers=1) as executor:
            original = executor.submit(worker.process_next_job)
            try:
                assert started.wait(30)
                assert worker.recover_abandoned_jobs() == 0
                with engine.begin() as db:
                    assert db.execute(text("SELECT pg_terminate_backend(:pid, 5000)"),
                                      {"pid": observed["pid"]}).scalar_one()
                assert worker.recover_abandoned_jobs() == 1
                assert worker.process_next_job() is True
            finally:
                release.set()
                assert original.result(timeout=30) is True
        with Session(engine) as db:
            completed = db.get(BackgroundJob, job_id)
            assert completed.status == "EXITOSO" and completed.attempts == 2 and not completed.active
            path = result_artifact_path(public_id, completed.result)
            assert path.read_bytes() == b"recovered attempt"
            assert completed.result["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
            assert len(list(tmp_path.glob("*.csv"))) == 2
        app.dependency_overrides[get_db] = database
        try:
            with TestClient(app) as client:
                response = client.get(f"/api/exports/{public_id}/download",
                                      headers={"X-Export-Token": create_export_token(public_id, expiry)})
        finally:
            app.dependency_overrides.pop(get_db, None)
        assert response.status_code == 200 and response.content == b"recovered attempt"
        monkeypatch.setattr("shared.export_artifacts.settings.EXPORT_ARTIFACT_TTL_HOURS", 1)
        removed = cleanup_expired_artifacts(now=time.time() + 3601, directory=tmp_path)
        assert removed == 2 and not list(tmp_path.glob("*.csv"))
        print("EXPORT_RECOVERY_EVIDENCE=" + json.dumps({
            "status": "EXITOSO", "attempts": 2, "download_http_status": response.status_code,
            "download_matches_recovered_attempt": True, "checksum_matches_download": True,
            "late_attempt_replaced_confirmed_artifact": False,
            "expired_attempt_files_removed": removed,
        }))
    finally:
        release.set()
        app.dependency_overrides.pop(get_db, None)
        if job_id is not None:
            with engine.begin() as db:
                db.execute(delete(BackgroundJob).where(BackgroundJob.id == job_id))
        engine.dispose()
