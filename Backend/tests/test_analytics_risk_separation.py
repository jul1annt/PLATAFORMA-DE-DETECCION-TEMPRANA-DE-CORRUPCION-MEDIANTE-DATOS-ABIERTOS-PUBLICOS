from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from core.database import get_db
from gateway.middlewares.auth_middleware import get_current_admin
from main import app
from modules.analitica.controller import AnaliticaController
from modules.analitica.repository.repository import AnaliticaRepository
from modules.analitica.services.AnaliticaService import (
    EjecucionesAnaliticasIncompatiblesError,
    AnaliticaService,
    FaltanEjecucionesAnaliticasError,
)


def test_execution_status_becomes_outdated_when_contract_universe_changes():
    signature_at_run = {"total_contratos": 1, "id_maximo": 1}
    current_signature = {"total_contratos": 2, "id_maximo": 2}
    repository = object.__new__(AnaliticaRepository)
    repository.obtener_ejecucion_analitica = lambda _run_id: SimpleNamespace(
        estado="EXITOSO", firma_universo=signature_at_run
    )
    repository.obtener_firma_universo = lambda: current_signature

    assert repository.obtener_estado_ejecucion_analitica("run-1") == "DESACTUALIZADO"


def test_execution_status_preserves_failure_and_current_success():
    signature = {"total_contratos": 1, "id_maximo": 1}
    repository = object.__new__(AnaliticaRepository)
    repository.obtener_firma_universo = lambda: signature

    repository.obtener_ejecucion_analitica = lambda _run_id: SimpleNamespace(
        estado="EXITOSO", firma_universo=signature
    )
    assert repository.obtener_estado_ejecucion_analitica("run-1") == "EXITOSO"

    repository.obtener_ejecucion_analitica = lambda _run_id: SimpleNamespace(
        estado="ERROR", firma_universo=signature
    )
    assert repository.obtener_estado_ejecucion_analitica("run-2") == "ERROR"


def test_latest_execution_statuses_include_failed_runs_without_results():
    started = datetime.now(timezone.utc)
    run = SimpleNamespace(
        tipo="OUTLIERS", run_id=uuid4(), estado="ERROR",
        fecha_inicio=started, fecha_fin=started,
    )

    class Repository:
        def obtener_ultima_ejecucion_analitica(self, tipo):
            return run if tipo == "OUTLIERS" else None

        def obtener_estado_ejecucion_analitica(self, _run_id):
            return "ERROR"

    service = AnaliticaService(object())
    service.repo = Repository()

    statuses = service.obtener_estados_ultimas_ejecuciones()

    assert len(statuses) == 1
    assert statuses[0].tipo == "OUTLIERS"
    assert statuses[0].estado == "ERROR"


def test_latest_execution_status_endpoint_reports_failure_to_admin(monkeypatch):
    started = datetime.now(timezone.utc)
    status = SimpleNamespace(
        tipo="OUTLIERS", run_id=uuid4(), estado="ERROR",
        fecha_inicio=started, fecha_fin=started,
    )
    monkeypatch.setattr(
        AnaliticaController,
        "AnaliticaService",
        lambda _db: SimpleNamespace(obtener_estados_ultimas_ejecuciones=lambda: [status]),
    )
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(id=1)

    try:
        response = TestClient(app).get("/api/analitica/ejecuciones/ultimas")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_admin, None)

    assert response.status_code == 200
    assert response.json()[0]["estado"] == "ERROR"


def test_provider_risk_calculation_does_not_project_to_contracts():
    contract = SimpleNamespace(
        clasificacion_riesgo="SIN_EVALUAR",
        score_riesgo=None,
        riesgo_run_id=None,
    )

    class Session:
        commits = 0

        def commit(self):
            self.commits += 1

        def rollback(self):
            return None

    class Repository:
        def __init__(self):
            self.saved = []
            self.firma = {"total_contratos": 1, "id_maximo": 1, "ultimo_procesado_en": "2026-01-01T00:00:00+00:00"}

        def obtener_firma_universo(self):
            return self.firma

        def obtener_estado_ejecucion_analitica(self, _run_id):
            return "EN_PROCESO"

        def iniciar_ejecucion_analitica(self, **_kwargs):
            return None

        def finalizar_ejecucion_analitica(self, *_args, **_kwargs):
            return None

        def actualizar_contexto_ejecucion(self, *_args, **_kwargs):
            return None

        def obtener_pesos(self):
            return [SimpleNamespace(tipo_anomalia="OUTLIER", peso=Decimal("1"))]

        def obtener_ejecuciones_componentes_riesgo(self):
            scope = {
                "fecha_campo": "fecha_publicacion_normalizada",
                "fecha_desde": None,
                "fecha_hasta": None,
                "modalidad": None,
            }
            return {
                name: SimpleNamespace(
                    run_id=name,
                    estado="EXITOSO",
                    universo=scope,
                    firma_universo=self.firma,
                )
                for name in ("outliers", "duplicados", "adjudicacion_directa")
            }

        def obtener_scores_combinados_por_proveedor(self, _ejecuciones):
            return [{
                "proveedor": "Proveedor con riesgo alto",
                "nit_proveedor": "900123456",
                "max_score_outlier": 6,
                "max_score_duplicado": 0,
                "score_directo": 0,
            }]

        def guardar_riesgo_proveedores(self, registros):
            self.saved.extend(registros)

        def aplicar_riesgo_a_contratos(self, _run_id):
            contract.clasificacion_riesgo = "ALTO"
            contract.score_riesgo = Decimal("6")
            contract.riesgo_run_id = _run_id
            raise AssertionError("El riesgo del proveedor no se debe proyectar al contrato")

        def obtener_resumen_riesgo(self, run_id):
            return {
                "resumen": {
                    "run_id": run_id,
                    "total_proveedores_evaluados": 1,
                    "promedio_score_final": Decimal("6"),
                    "fecha_calculo": datetime.now(timezone.utc),
                },
                "por_riesgo": [{"riesgo": "ALTO", "total": 1}],
            }

    session = Session()
    repository = Repository()
    service = AnaliticaService(session)
    service.repo = repository

    result = service.calcular_riesgo_global()

    assert session.commits == 1
    assert len(repository.saved) == 1
    assert repository.saved[0].clasificacion_riesgo == "ALTO"
    assert repository.saved[0].pesos_aplicados["run_ids"] == {
        "outliers": "outliers",
        "duplicados": "duplicados",
        "adjudicacion_directa": "adjudicacion_directa",
    }
    assert result.total_proveedores_evaluados == 1
    assert contract.clasificacion_riesgo == "SIN_EVALUAR"
    assert contract.score_riesgo is None
    assert contract.riesgo_run_id is None


def test_successful_risk_run_with_no_findings_is_still_recorded():
    class Session:
        def commit(self):
            return None

        def rollback(self):
            raise AssertionError("No se esperaba rollback")

    class Repository:
        firma = {"total_contratos": 0, "id_maximo": 0, "ultimo_procesado_en": None}
        scope = {
            "fecha_campo": "fecha_publicacion_normalizada",
            "fecha_desde": None,
            "fecha_hasta": None,
            "modalidad": None,
        }

        def __init__(self):
            self.finalized = None

        def obtener_firma_universo(self):
            return self.firma

        def iniciar_ejecucion_analitica(self, **_kwargs):
            return None

        def finalizar_ejecucion_analitica(self, _run_id, **kwargs):
            self.finalized = kwargs

        def actualizar_contexto_ejecucion(self, *_args, **_kwargs):
            return None

        def obtener_estado_ejecucion_analitica(self, _run_id):
            return "EN_PROCESO"

        def obtener_pesos(self):
            return []

        def obtener_ejecuciones_componentes_riesgo(self):
            return {
                name: SimpleNamespace(
                    run_id=name,
                    estado="EXITOSO",
                    universo=self.scope,
                    firma_universo=self.firma,
                )
                for name in ("outliers", "duplicados", "adjudicacion_directa")
            }

        def obtener_scores_combinados_por_proveedor(self, _ejecuciones):
            return []

        def obtener_resumen_riesgo(self, _run_id):
            return {"resumen": {}, "por_riesgo": []}

    repository = Repository()
    service = AnaliticaService(Session())
    service.repo = repository

    result = service.calcular_riesgo_global()

    assert result.total_proveedores_evaluados == 0
    assert result.estado_ejecucion == "EXITOSO"
    assert repository.finalized["estado"] == "EXITOSO"
    assert repository.finalized["total_resultados"] == 0


def test_provider_risk_calculation_rejects_missing_component_runs():
    class Session:
        commits = 0

        def commit(self):
            self.commits += 1

        def rollback(self):
            return None

    class Repository:
        firma = {"total_contratos": 1, "id_maximo": 1, "ultimo_procesado_en": "2026-01-01T00:00:00+00:00"}

        def obtener_firma_universo(self):
            return self.firma

        def iniciar_ejecucion_analitica(self, **_kwargs):
            return None

        def finalizar_ejecucion_analitica(self, *_args, **_kwargs):
            return None

        def obtener_pesos(self):
            return []

        def obtener_ejecuciones_componentes_riesgo(self):
            return {"outliers": "outlier-run", "duplicados": None, "adjudicacion_directa": "direct-run"}

        def obtener_scores_combinados_por_proveedor(self, _ejecuciones):
            raise AssertionError("No se deben combinar entradas incompletas")

    session = Session()
    service = AnaliticaService(session)
    service.repo = Repository()

    try:
        service.calcular_riesgo_global()
    except FaltanEjecucionesAnaliticasError as exc:
        assert "duplicados" in str(exc)
    else:
        raise AssertionError("Se esperaba rechazar un cálculo con una ejecución faltante")

    assert session.commits == 0


def test_provider_risk_calculation_rejects_incompatible_component_scopes():
    class Session:
        commits = 0
        rollbacks = 0

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

    class Repository:
        firma = {"total_contratos": 2, "id_maximo": 2, "ultimo_procesado_en": "2026-01-01T00:00:00+00:00"}

        def __init__(self):
            self.context_updated = False

        def obtener_firma_universo(self):
            return self.firma

        def iniciar_ejecucion_analitica(self, **_kwargs):
            return None

        def finalizar_ejecucion_analitica(self, *_args, **_kwargs):
            return None

        def obtener_pesos(self):
            return []

        def obtener_ejecuciones_componentes_riesgo(self):
            base_scope = {
                "fecha_campo": "fecha_publicacion_normalizada",
                "fecha_desde": None,
                "fecha_hasta": None,
                "modalidad": None,
            }
            incompatible_scope = {**base_scope, "fecha_desde": "2026-01-01"}
            return {
                name: SimpleNamespace(
                    run_id=name,
                    estado="EXITOSO",
                    universo=incompatible_scope if name == "duplicados" else base_scope,
                    firma_universo=self.firma,
                )
                for name in ("outliers", "duplicados", "adjudicacion_directa")
            }

        def actualizar_contexto_ejecucion(self, *_args, **_kwargs):
            self.context_updated = True

    session = Session()
    repository = Repository()
    service = AnaliticaService(session)
    service.repo = repository

    try:
        service.calcular_riesgo_global()
    except EjecucionesAnaliticasIncompatiblesError:
        pass
    else:
        raise AssertionError("Se esperaba rechazar ejecuciones con filtros incompatibles")

    assert repository.context_updated is False
    assert session.commits == 0
    assert session.rollbacks == 1


def test_api_enqueues_risk_calculation_for_background_validation(monkeypatch):
    queued = {}

    def fake_enqueue(_db, *, kind, payload, resource_key):
        queued.update(kind=kind, payload=payload, resource_key=resource_key)
        return SimpleNamespace(
            public_id=uuid4(), kind=kind, status="PENDIENTE"
        ), True

    monkeypatch.setattr(AnaliticaController, "enqueue_job", fake_enqueue)
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_admin] = lambda: object()
    try:
        response = TestClient(app).post("/api/analitica/riesgo/calcular")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_admin, None)

    assert response.status_code == 202
    assert response.json()["kind"] == "ANALITICA"
    assert queued == {
        "kind": "ANALITICA",
        "payload": {"tipo": "RIESGO", "parametros": {}},
        "resource_key": "analitica:RIESGO",
    }


def test_api_rejects_conflicting_parameters_for_active_analytic_job(monkeypatch):
    active = SimpleNamespace(
        public_id=uuid4(), kind="ANALITICA", status="EN_PROCESO",
        payload={"tipo": "RIESGO", "parametros": {"old": True}},
    )
    monkeypatch.setattr(
        AnaliticaController,
        "enqueue_job",
        lambda *_args, **_kwargs: (active, False),
    )
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_admin] = lambda: object()
    try:
        response = TestClient(app).post("/api/analitica/riesgo/calcular")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_admin, None)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Ya hay un cálculo de este tipo en curso con otros parámetros."
    )
