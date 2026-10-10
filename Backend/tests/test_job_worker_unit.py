import builtins
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from modules.jobs import worker


def mock_pinned_session(monkeypatch, database):
    @contextmanager
    def session():
        try:
            yield database, lambda: True
        finally:
            database.close()
    monkeypatch.setattr(worker, "_pinned_session", session)


def test_job_dispatch_does_not_import_unrelated_executor(monkeypatch):
    class Database:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class Ingesta:
        def __init__(self, _db):
            pass

        def sincronizar_fuente(self, source_id, job_id):
            return {"fuente_id": source_id, "job_id": job_id}

    monkeypatch.setattr(worker, "SessionLocal", Database)
    monkeypatch.setattr(worker, "IngestaService", Ingesta)
    original_import = builtins.__import__

    def fail_analytics_import(name, *args, **kwargs):
        if name.startswith("modules.analitica.services"):
            raise ImportError("analytics unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_analytics_import)

    assert worker._execute("INGESTA", {"fuente_id": 3}, job_id=10) == {
        "fuente_id": 3, "job_id": 10,
    }


def test_worker_hides_internal_exception_details_from_job_and_logs(monkeypatch, caplog):
    secret = "database-password=must-not-leak"
    job = SimpleNamespace(
        id=81,
        kind="TEST",
        payload={},
        public_id="job-test",
        status="PENDIENTE",
        active=True,
        attempts=0,
        started_at=None,
        finished_at=None,
        error_id=None,
        error_message=None,
        result=None,
    )

    class Query:
        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def with_for_update(self, **_kwargs):
            return self

        def first(self):
            return job

        def one(self):
            return job

    class Result:
        def scalar(self):
            return True

    class Database:
        closed = False

        def __init__(self):
            self.commits = 0
            self.sql = []

        def query(self, _model):
            return Query()

        def execute(self, statement, _params=None):
            self.sql.append(str(statement))
            return Result()

        def commit(self):
            self.commits += 1

        def rollback(self):
            pass

        def close(self):
            self.closed = True

    database = Database()

    def fail_job(*_args, **_kwargs):
        raise RuntimeError(secret)

    mock_pinned_session(monkeypatch, database)
    monkeypatch.setattr(worker, "_execute", fail_job)
    caplog.set_level("ERROR")

    assert worker.process_next_job() is True

    assert job.status == "ERROR"
    assert job.active is False
    assert job.finished_at is not None
    assert job.error_id is not None
    assert job.error_message == f"Error interno. Referencia: {job.error_id}"
    assert secret not in job.error_message
    assert secret not in caplog.text
    assert "RuntimeError" in caplog.text
    assert str(job.error_id) in caplog.text
    assert "pg_advisory_unlock" in database.sql[-1]
    assert database.closed is True
    assert database.commits >= 2


def test_worker_marks_capped_ingestion_as_partial(monkeypatch):
    job = SimpleNamespace(
        id=82,
        kind="INGESTA",
        payload={"fuente_id": 1},
        public_id="job-partial",
        status="PENDIENTE",
        active=True,
        attempts=0,
        started_at=None,
        finished_at=None,
        error_id=None,
        error_message=None,
        result=None,
    )

    class Query:
        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def with_for_update(self, **_kwargs):
            return self

        def first(self):
            return job

        def one(self):
            return job

    class Result:
        def scalar(self):
            return True

    class Database:
        def __init__(self):
            self.closed = False

        def query(self, _model):
            return Query()

        def execute(self, *_args, **_kwargs):
            return Result()

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            self.closed = True

    database = Database()
    mock_pinned_session(monkeypatch, database)
    monkeypatch.setattr(
        worker,
        "_execute",
        lambda *_args, **_kwargs: {"parcial": True, "registros_traidos": 10000},
    )

    assert worker.process_next_job() is True

    assert job.status == "PARCIAL"
    assert job.active is False
    assert job.result == {"parcial": True, "registros_traidos": 10000}
    assert job.finished_at is not None
    assert database.closed is True


@pytest.mark.parametrize(
    ("tipo", "parametros", "method"),
    [
        ("OUTLIERS", {"campo": "precio_base_normalizado"}, "calcular_outliers"),
        ("DUPLICADOS", {}, "calcular_duplicados"),
        ("ADJUDICACION_DIRECTA", {"minimo_directas": 4}, "calcular_abuso_adjudicacion_directa"),
        ("RIESGO", {}, "calcular_riesgo_global"),
    ],
)
def test_worker_runs_analytic_jobs_and_serializes_pydantic_results(
    monkeypatch, tipo, parametros, method
):
    called = []

    class Database:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class Summary(BaseModel):
        tipo: str
        campo: str | None = None
        minimo_directas: int | None = None

    class FakeAnaliticaService:
        def __init__(self, _db):
            pass

        def calcular_outliers(self, request):
            called.append("calcular_outliers")
            assert request.campo == parametros["campo"]
            return Summary(tipo=tipo, campo=request.campo)

        def calcular_duplicados(self, request):
            called.append("calcular_duplicados")
            assert request.fecha_desde is None
            assert request.fecha_hasta is None
            return Summary(tipo=tipo)

        def calcular_abuso_adjudicacion_directa(self, request):
            called.append("calcular_abuso_adjudicacion_directa")
            assert request.minimo_directas == parametros["minimo_directas"]
            return Summary(tipo=tipo, minimo_directas=request.minimo_directas)

        def calcular_riesgo_global(self):
            called.append("calcular_riesgo_global")
            return Summary(tipo=tipo)

    monkeypatch.setattr(worker, "SessionLocal", Database)
    monkeypatch.setattr(worker, "AnaliticaService", FakeAnaliticaService)

    result = worker._execute(
        "ANALITICA", {"tipo": tipo, "parametros": parametros}
    )

    assert result["tipo"] == tipo
    assert called == [method]
    if tipo == "OUTLIERS":
        assert result["campo"] == parametros["campo"]
    if tipo == "ADJUDICACION_DIRECTA":
        assert result["minimo_directas"] == parametros["minimo_directas"]
