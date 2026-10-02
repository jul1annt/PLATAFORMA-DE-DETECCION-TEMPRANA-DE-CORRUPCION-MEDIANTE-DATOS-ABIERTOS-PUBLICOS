"""PostgreSQL integration coverage for analytics above the former 1,000-row cap.

This test deliberately requires an explicit loopback TEST_DATABASE_URL whose
database name contains "test". It never uses the application's .env database.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import text

from modules.analitica.model.contrato_duplicado_periodo import ContratoDuplicadoPeriodo
from modules.analitica.model.contrato_outlier import ContratoOutlier
from modules.analitica.repository.repository import AnaliticaRepository
from modules.analitica.model.riesgo_proveedor import RiesgoProveedor
from modules.analitica.services.AnaliticaService import AnaliticaService
from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.transformacion.dto.request import ContratoProcesadoFilterDTO
from modules.transformacion.model.ContratoProcesado import ContratoProcesado
from modules.ingesta.model.RawSecop import RawSecop
from modules.transformacion.repository.transformacion import TransformacionRepository
from shared.enums import TipoFormato


def test_large_analytics_work_mem_is_transaction_local(postgres_test_session):
    session = postgres_test_session
    before = session.execute(text("SHOW work_mem")).scalar_one()
    AnaliticaRepository(session)._configure_large_query_memory()
    assert session.execute(text("SHOW work_mem")).scalar_one() == "32MB"
    session.rollback()
    assert session.execute(text("SHOW work_mem")).scalar_one() == before


def test_analytics_queries_include_contracts_beyond_one_thousand(postgres_test_session):
    session = postgres_test_session
    suffix = uuid.uuid4().hex
    source = FuenteDatos(
        nombre=f"pytest-analytics-{suffix}",
        tipo="TEST",
        formato=TipoFormato.JSON,
        endpoint="https://example.test/resource/contracts.json",
        activo=True,
    )
    session.add(source)
    session.flush()

    raw_rows = [
        RawSecop(
            fuente_id=source.id,
            id_del_proceso=f"pytest-{suffix}-{index}",
        )
        for index in range(1001)
    ]
    session.add_all(raw_rows)
    session.flush()

    contracts = [
        ContratoProcesado(
            raw_secop_id=raw.id,
            id_del_proceso=raw.id_del_proceso,
            # Homónimos deben seguir separados por NIT en el ranking.
            proveedor_normalizado="Proveedor de prueba",
            nit_proveedor="900000001" if index < 1000 else "900000002",
            nit_proveedor_clave="900000001" if index < 1000 else "900000002",
            normalized_hash=hashlib.sha256(f"{suffix}-{index}".encode()).hexdigest(),
            es_incompleto=index == 0,
            es_sospechoso=index == 0,
            nivel_confianza=100,
            clasificacion_riesgo="ALTO" if index == 0 else "SIN_EVALUAR",
        )
        for index, raw in enumerate(raw_rows)
    ]
    session.add_all(contracts)
    session.flush()

    repository = TransformacionRepository(session)
    _, total = repository.search_contratos(ContratoProcesadoFilterDTO(), skip=1000, limit=50)
    metrics = repository.get_dashboard_metricas()
    risk_distribution = repository.get_risk_distribution()
    top_providers = repository.get_top_providers(limit=10)

    assert total == 1001
    assert metrics["total_contratos"] == 1001
    assert metrics["total_incompletos"] == 1
    assert metrics["total_sospechosos"] == 1
    assert metrics["total_alto_riesgo"] == 1
    assert sum(item["value"] for item in risk_distribution) == 1001
    assert top_providers[0] == {
        "nit": "900000001",
        "name": "Proveedor de prueba",
        "contracts": 1000,
    }
    assert top_providers[1] == {
        "nit": "900000002",
        "name": "Proveedor de prueba",
        "contracts": 1,
    }


def test_provider_risk_calculation_does_not_classify_contracts(postgres_test_session):
    session = postgres_test_session
    suffix = uuid.uuid4().hex
    source = FuenteDatos(
        nombre=f"pytest-provider-risk-{suffix}",
        tipo="TEST",
        formato=TipoFormato.JSON,
        endpoint="https://example.test/resource/contracts.json",
        activo=True,
    )
    session.add(source)
    session.flush()
    raw = RawSecop(
        fuente_id=source.id,
        id_del_proceso=f"pytest-provider-risk-{suffix}",
    )
    session.add(raw)
    session.flush()
    contract = ContratoProcesado(
        raw_secop_id=raw.id,
        id_del_proceso=raw.id_del_proceso,
        proveedor_normalizado="Proveedor con riesgo alto",
        nit_proveedor="900123456",
        normalized_hash=hashlib.sha256(suffix.encode()).hexdigest(),
        clasificacion_riesgo="SIN_EVALUAR",
    )
    session.add(contract)
    session.flush()

    service = AnaliticaService(session)
    firma = {"total_contratos": 1, "id_maximo": 1, "ultimo_procesado_en": "2026-01-01T00:00:00+00:00"}
    scope = {
        "fecha_campo": "fecha_publicacion_normalizada",
        "fecha_desde": None,
        "fecha_hasta": None,
        "modalidad": None,
    }
    from types import SimpleNamespace

    service.repo.obtener_pesos = lambda: [
        SimpleNamespace(tipo_anomalia="OUTLIER", peso=Decimal("1")),
    ]
    service.repo.obtener_ejecuciones_componentes_riesgo = lambda: {
        name: SimpleNamespace(
            run_id=uuid.uuid4(), estado="EXITOSO", universo=scope, firma_universo=firma
        )
        for name in ("outliers", "duplicados", "adjudicacion_directa")
    }
    service.repo.obtener_firma_universo = lambda: firma
    service.repo.obtener_scores_combinados_por_proveedor = lambda _ejecuciones: [{
        "proveedor": "Proveedor con riesgo alto",
        "nit_proveedor": "900123456",
        "max_score_outlier": 6,
        "max_score_duplicado": 0,
        "score_directo": 0,
    }]

    summary = service.calcular_riesgo_global()

    session.refresh(contract)
    proveedor_riesgo = session.query(RiesgoProveedor).filter_by(
        run_id=summary.run_id,
        nit_proveedor="900123456",
    ).one()
    assert proveedor_riesgo.clasificacion_riesgo == "ALTO"
    assert contract.clasificacion_riesgo == "SIN_EVALUAR"
    assert contract.score_riesgo is None
    assert contract.riesgo_run_id is None


def test_outlier_and_duplicate_results_are_inserted_by_postgres(postgres_test_session):
    session = postgres_test_session
    suffix = uuid.uuid4().hex
    source = FuenteDatos(
        nombre=f"pytest-analytics-sql-{suffix}",
        tipo="TEST",
        formato=TipoFormato.JSON,
        endpoint=f"https://example.test/resource/{suffix}",
        activo=True,
    )
    session.add(source)
    session.flush()

    values = [Decimal("100"), Decimal("120"), Decimal("130"), Decimal("1000")]
    raw_rows = [
        RawSecop(fuente_id=source.id, id_del_proceso=f"pytest-sql-{suffix}-{index}")
        for index in range(len(values))
    ]
    session.add_all(raw_rows)
    session.flush()

    contracts = [
        ContratoProcesado(
            raw_secop_id=raw.id,
            id_del_proceso=raw.id_del_proceso,
            proveedor_normalizado=f"Proveedor {suffix}",
            entidad_normalizada=f"Entidad {suffix}",
            fecha_publicacion_normalizada=date(2026, 1, 1 + index * 3),
            valor_total_normalizado=value,
            tipo_contrato_normalizado="Servicios",
            modalidad_contratacion=f"Prueba {suffix}",
            normalized_hash=hashlib.sha256(f"{suffix}-{index}".encode()).hexdigest(),
            es_incompleto=False,
        )
        for index, (raw, value) in enumerate(zip(raw_rows, values, strict=True))
    ]
    session.add_all(contracts)
    session.flush()

    repository = AnaliticaRepository(session)
    start, end = date(2026, 1, 1), date(2026, 1, 31)
    modalidad = f"Prueba {suffix}"
    stats = repository.obtener_estadisticas_por_grupo(
        campo="valor_total_normalizado",
        fecha_desde=start,
        fecha_hasta=end,
        modalidad=modalidad,
    )
    outlier_run_id = uuid.uuid4()
    analyzed, outliers = repository.guardar_resultados_outliers_sql(
        run_id=outlier_run_id,
        campo="valor_total_normalizado",
        estadisticas_por_grupo={row["grupo"]: row for row in stats},
        fecha_calculo=datetime.now(timezone.utc),
        fecha_desde=start,
        fecha_hasta=end,
        modalidad=modalidad,
    )

    duplicate_run_id = uuid.uuid4()
    duplicates = repository.guardar_duplicados_sql(
        run_id=duplicate_run_id,
        fecha_calculo=datetime.now(timezone.utc),
        fecha_desde=start,
        fecha_hasta=end,
    )
    own_duplicates = session.query(ContratoDuplicadoPeriodo).filter_by(
        run_id=duplicate_run_id,
        proveedor=f"Proveedor {suffix}",
    ).count()

    assert analyzed == 4
    assert outliers == 1
    assert duplicates >= 3
    assert own_duplicates == 3


def test_outlier_score_accepts_large_statistical_outliers(postgres_test_session):
    session = postgres_test_session
    suffix = uuid.uuid4().hex
    source = FuenteDatos(
        nombre=f"pytest-analytics-score-{suffix}",
        tipo="TEST",
        formato=TipoFormato.JSON,
        endpoint=f"https://example.test/resource/{suffix}",
        activo=True,
    )
    session.add(source)
    session.flush()

    values = [Decimal("100"), Decimal("100.5"), Decimal("101"), Decimal("101.5"), Decimal("102"), Decimal("9000000000000")]
    raw_rows = [
        RawSecop(fuente_id=source.id, id_del_proceso=f"pytest-score-{suffix}-{index}")
        for index in range(len(values))
    ]
    session.add_all(raw_rows)
    session.flush()
    session.add_all([
        ContratoProcesado(
            raw_secop_id=raw.id,
            id_del_proceso=raw.id_del_proceso,
            proveedor_normalizado=f"Proveedor {suffix}",
            entidad_normalizada=f"Entidad {suffix}",
            fecha_publicacion_normalizada=date(2026, 1, 1 + index),
            valor_total_normalizado=value,
            tipo_contrato_normalizado="Servicios",
            modalidad_contratacion=f"Prueba score {suffix}",
            normalized_hash=hashlib.sha256(f"score-{suffix}-{index}".encode()).hexdigest(),
            es_incompleto=False,
        )
        for index, (raw, value) in enumerate(zip(raw_rows, values, strict=True))
    ])
    session.flush()

    repository = AnaliticaRepository(session)
    modalidad = f"Prueba score {suffix}"
    stats = repository.obtener_estadisticas_por_grupo(
        campo="valor_total_normalizado",
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 1, 31),
        modalidad=modalidad,
    )
    run_id = uuid.uuid4()
    analyzed, outliers = repository.guardar_resultados_outliers_sql(
        run_id=run_id,
        campo="valor_total_normalizado",
        estadisticas_por_grupo={row["grupo"]: row for row in stats},
        fecha_calculo=datetime.now(timezone.utc),
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 1, 31),
        modalidad=modalidad,
    )
    saved_score = session.query(ContratoOutlier.score).filter_by(
        run_id=run_id,
        contrato_id=session.query(ContratoProcesado.id).filter_by(
            raw_secop_id=raw_rows[-1].id
        ).scalar_subquery(),
    ).one()[0]

    assert analyzed == 6
    assert outliers == 1
    assert saved_score > Decimal("999999.9999")
