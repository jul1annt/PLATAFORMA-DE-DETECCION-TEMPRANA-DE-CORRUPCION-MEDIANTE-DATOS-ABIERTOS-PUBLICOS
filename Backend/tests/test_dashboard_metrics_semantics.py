from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from modules.transformacion.dto.response import DashboardMetricasDTO, MetricasCalidadDTO
from modules.transformacion.repository.transformacion import TransformacionRepository


def _repository_for(rows):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("""
            CREATE TABLE contratos_procesados (
                id INTEGER PRIMARY KEY,
                es_incompleto BOOLEAN,
                es_sospechoso BOOLEAN,
                nivel_confianza INTEGER,
                clasificacion_riesgo TEXT,
                nit_proveedor_clave TEXT,
                proveedor_normalizado TEXT
            )
        """)
        if rows:
            connection.exec_driver_sql(
                """INSERT INTO contratos_procesados
                   (id, es_incompleto, es_sospechoso, nivel_confianza, clasificacion_riesgo)
                   VALUES (?, ?, ?, ?, ?)""",
                rows,
            )
    return engine


def test_empty_dataset_returns_no_confidence_or_percentages():
    engine = _repository_for([])
    try:
        with Session(engine) as session:
            repository = TransformacionRepository(session)
            metrics = repository.get_metricas_calidad()
            dashboard = repository.get_dashboard_metricas()

        quality_response = MetricasCalidadDTO.model_validate(metrics)
        dashboard_response = DashboardMetricasDTO.model_validate(dashboard)

        assert quality_response.total_contratos == 0
        assert quality_response.promedio_confianza is None
        assert quality_response.calificacion_confianza == "SIN_DATOS"
        assert quality_response.porcentaje_completos is None
        assert quality_response.porcentaje_incompletos is None
        assert quality_response.porcentaje_sospechosos is None
        assert dashboard_response.estado_datos == "SIN_DATOS"
        assert dashboard_response.total_completos == 0
        assert dashboard_response.promedio_confianza is None
        assert dashboard_response.pct_alto_riesgo is None
    finally:
        engine.dispose()


def test_dashboard_confidence_category_is_computed_by_backend():
    cases = [
        ([(1, False, False, 90, "SIN_EVALUAR"), (2, True, True, 60, "ALTO")], "ACEPTABLE", 75.0),
        ([(1, False, False, 100, "SIN_EVALUAR"), (2, False, False, 60, "BAJO")], "EXCELENTE", 80.0),
        ([(1, True, False, 40, "SIN_EVALUAR"), (2, False, False, 50, "MEDIO")], "BAJA", 45.0),
    ]

    for rows, expected_category, expected_average in cases:
        engine = _repository_for(rows)
        try:
            with Session(engine) as session:
                dashboard = TransformacionRepository(session).get_dashboard_metricas()

            assert dashboard["estado_datos"] == "DISPONIBLE"
            assert dashboard["total_completos"] == sum(not row[1] for row in rows)
            assert dashboard["calificacion_confianza"] == expected_category
            assert dashboard["promedio_confianza"] == expected_average
        finally:
            engine.dispose()


def test_dashboard_aggregates_the_entire_universe_in_one_sql_statement():
    rows = [
        (index, index == 1001, index == 1001, 80, "ALTO" if index == 1001 else "SIN_EVALUAR")
        for index in range(1, 1002)
    ]
    engine = _repository_for(rows)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE contratos_procesados SET nit_proveedor_clave = '900000001', proveedor_normalizado = 'Proveedor repetido' WHERE id <= 1000"
        )
        connection.exec_driver_sql(
            "UPDATE contratos_procesados SET nit_proveedor_clave = '900000002', proveedor_normalizado = 'Proveedor repetido' WHERE id = 1001"
        )
    statements = []
    event.listen(
        engine,
        "before_cursor_execute",
        lambda _conn, _cursor, statement, _parameters, _context, _many: statements.append(statement),
    )
    try:
        with Session(engine) as session:
            repository = TransformacionRepository(session)
            dashboard = repository.get_dashboard_metricas()
            dashboard_selects = [
                statement for statement in statements
                if statement.lstrip().upper().startswith("SELECT")
            ]
            statements.clear()
            anomaly_distribution = repository.get_anomaly_distribution()
            anomaly_selects = [
                statement for statement in statements
                if statement.lstrip().upper().startswith("SELECT")
            ]
            statements.clear()
            risk_distribution = repository.get_risk_distribution()
            risk_selects = [
                statement for statement in statements
                if statement.lstrip().upper().startswith("SELECT")
            ]
            statements.clear()
            top_providers = repository.get_top_providers(limit=10)
            ranking_selects = [
                statement for statement in statements
                if statement.lstrip().upper().startswith("SELECT")
            ]

        assert dashboard["total_contratos"] == 1001
        assert dashboard["total_incompletos"] == 1
        assert dashboard["total_alto_riesgo"] == 1
        assert len(dashboard_selects) == 1
        assert sum(item["value"] for item in anomaly_distribution) == 3
        assert len(anomaly_selects) == 1
        assert sum(item["value"] for item in risk_distribution) == 1001
        assert len(risk_selects) == 1
        assert [item["contracts"] for item in top_providers] == [1000, 1]
        assert len(ranking_selects) == 1
    finally:
        engine.dispose()
