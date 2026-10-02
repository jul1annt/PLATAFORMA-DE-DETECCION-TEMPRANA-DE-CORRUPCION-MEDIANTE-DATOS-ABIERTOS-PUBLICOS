from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from modules.transformacion.dto.request import ContratoProcesadoFilterDTO
from modules.transformacion.repository.transformacion import TransformacionRepository


def _engine_with_contracts():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE contratos_procesados (
                id INTEGER PRIMARY KEY,
                raw_secop_id INTEGER,
                id_del_proceso TEXT,
                entidad_normalizada TEXT,
                nit_entidad TEXT,
                proveedor_normalizado TEXT,
                nit_proveedor TEXT,
                nit_proveedor_clave TEXT,
                fecha_publicacion_normalizada DATE,
                fecha_adjudicacion_normalizada DATE,
                valor_total_normalizado NUMERIC,
                precio_base_normalizado NUMERIC,
                tipo_contrato_normalizado TEXT,
                modalidad_contratacion TEXT,
                estado_normalizado TEXT,
                ciudad_entidad TEXT,
                departamento_entidad TEXT,
                urlproceso TEXT,
                normalized_hash TEXT,
                es_incompleto BOOLEAN,
                cantidad_campos_faltantes INTEGER,
                campos_faltantes TEXT,
                nivel_confianza INTEGER,
                es_sospechoso BOOLEAN,
                clasificacion_riesgo TEXT,
                score_riesgo NUMERIC,
                riesgo_run_id TEXT,
                created_at DATETIME,
                procesado_en DATETIME
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO contratos_procesados (
                id, id_del_proceso, entidad_normalizada, proveedor_normalizado,
                nit_proveedor, nit_proveedor_clave, valor_total_normalizado,
                modalidad_contratacion, estado_normalizado, nivel_confianza,
                es_incompleto, es_sospechoso, clasificacion_riesgo, normalized_hash
            ) VALUES
                (1, 'PROC-ACME-1', 'Alcaldía Norte', 'Acme SAS', '900111222-3', '900111222', 100, 'Licitación', 'Publicado', 90, 0, 0, 'ALTO', 'h1'),
                (2, 'PROC-ACME-2', 'Alcaldía Sur', 'Acme Servicios', '900333444-5', '900333444', 200, 'Licitación', 'Publicado', 80, 1, 0, 'ALTO', 'h2'),
                (3, 'PROC-OTHER', 'Acme Central', 'Otro Proveedor', '800555666-7', '800555666', 300, 'Directa', 'Cerrado', 70, 0, 1, 'BAJO', 'h3')
            """
        )
    return engine


def test_contract_search_applies_text_and_risk_filters_before_count_and_pagination():
    engine = _engine_with_contracts()
    try:
        with Session(engine) as session:
            items, total = TransformacionRepository(session).search_contratos(
                ContratoProcesadoFilterDTO(query="Acme", solo_alto_riesgo=True),
                skip=1,
                limit=1,
                sort="id",
                order="asc",
            )

        assert total == 2
        assert len(items) == 1
        assert items[0].id == 2
    finally:
        engine.dispose()


def test_autocomplete_returns_matching_entities_and_providers_within_limit():
    engine = _engine_with_contracts()
    try:
        with Session(engine) as session:
            results = TransformacionRepository(session).autocomplete("Acme", limit=3)

        assert {result["type"] for result in results} == {"ENTIDAD", "PROVEEDOR"}
        assert {result["text"] for result in results} == {
            "Acme Central",
            "Acme SAS",
            "Acme Servicios",
        }
        assert len(results) <= 3
    finally:
        engine.dispose()
