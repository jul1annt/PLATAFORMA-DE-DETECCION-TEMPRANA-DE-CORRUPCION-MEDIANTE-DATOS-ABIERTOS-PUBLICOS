import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from modules.analitica.repository.repository import AnaliticaRepository
from modules.transformacion.repository.transformacion import TransformacionRepository
from modules.transformacion.services.trasformacionservice import TransformacionService
from modules.transformacion.services.normalization_service import (
    normalize_provider_nit,
    normalize_provider_nit_identity,
)


@pytest.mark.parametrize("value", [None, "", "  ", "N/A", " sin informacion ", "sin información", "NO DEFINIDO", "-"])
def test_provider_nit_missing_markers_are_not_identity(value):
    assert normalize_provider_nit(value) is None


def test_provider_nit_keeps_reported_identifier_without_merging_by_name():
    assert normalize_provider_nit(" 900-123  ") == "900-123"


def test_provider_nit_identity_validates_optional_dian_check_digit():
    assert normalize_provider_nit_identity("860324218-1") == "860324218"
    assert normalize_provider_nit_identity("860.324.218-1") == "860324218"
    assert normalize_provider_nit_identity("860324218") == "860324218"
    assert normalize_provider_nit_identity("860324218-2") is None
    assert normalize_provider_nit_identity("900-123") is None
    assert normalize_provider_nit_identity("company-123") is None


def test_transformation_keeps_reported_nit_and_stores_separate_identity_key():
    raw = SimpleNamespace(
        id=9,
        id_del_proceso=None,
        entidad=None,
        nit_entidad=None,
        nombre_del_proveedor="Proveedor",
        nit_del_proveedor_adjudicado="860.324.218-1",
        fecha_de_publicacion_del=None,
        fecha_adjudicacion=None,
        valor_total_adjudicacion=None,
        precio_base=None,
        tipo_de_contrato=None,
        modalidad_de_contratacion=None,
        estado_del_procedimiento=None,
        ciudad_entidad=None,
        departamento_entidad=None,
        urlproceso=None,
    )

    normalized = TransformacionService(None)._normalizar(raw)

    assert normalized["nit_proveedor"] == "860.324.218-1"
    assert normalized["nit_proveedor_clave"] == "860324218"


def test_top_providers_group_by_normalized_nit_and_exclude_missing_markers():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("""
            CREATE TABLE contratos_procesados (
                id INTEGER PRIMARY KEY,
                nit_proveedor TEXT,
                nit_proveedor_clave TEXT,
                proveedor_normalizado TEXT
            )
        """)
        connection.exec_driver_sql("""
            INSERT INTO contratos_procesados VALUES
                (1, ' 900123456 ', '900123456', 'EMPRESA HOMONIMA'),
                (2, '900123456', '900123456', 'OTRO NOMBRE REPORTADO'),
                (3, '900000002', '900000002', 'EMPRESA HOMONIMA'),
                (4, 'N/A', NULL, 'PROVEEDOR SIN NIT'),
                (5, '   ', NULL, 'PROVEEDOR SIN NIT'),
                (6, '860324218-2', NULL, 'PROVEEDOR CON DV INVALIDO')
        """)

    with Session(engine) as session:
        top = TransformacionRepository(session).get_top_providers(limit=10)

    assert {item["nit"]: item["contracts"] for item in top} == {
        "900123456": 2,
        "900000002": 1,
    }
    assert {item["name"] for item in top if item["nit"] in {"900123456", "900000002"}} == {
        "EMPRESA HOMONIMA", "OTRO NOMBRE REPORTADO"
    }
    engine.dispose()


def test_combined_risk_uses_nit_as_key_and_ignores_missing_markers():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE contratos_procesados (id INTEGER PRIMARY KEY, nit_proveedor TEXT, nit_proveedor_clave TEXT, proveedor_normalizado TEXT)")
        connection.exec_driver_sql("CREATE TABLE contrato_outlier (run_id TEXT, contrato_id INTEGER, score NUMERIC)")
        connection.exec_driver_sql("CREATE TABLE contrato_duplicado_periodo (run_id TEXT, contrato_id INTEGER, duplicado_score NUMERIC)")
        connection.exec_driver_sql("CREATE TABLE proveedor_adjudicacion_directa (run_id TEXT, nit_proveedor TEXT, proveedor TEXT, score_riesgo NUMERIC)")
        connection.exec_driver_sql("""
            INSERT INTO contratos_procesados VALUES
                (1, ' 900123456 ', '900123456', 'EMPRESA HOMONIMA'),
                (2, '900123456', '900123456', 'OTRO NOMBRE REPORTADO'),
                (3, '900000002', '900000002', 'EMPRESA HOMONIMA'),
                (4, 'N/A', NULL, 'PROVEEDOR SIN NIT'),
                (5, '860324218-2', NULL, 'PROVEEDOR CON DV INVALIDO')
        """)
        connection.exec_driver_sql("""
            INSERT INTO contrato_outlier VALUES
                ('outliers', 1, 2.0), ('outliers', 2, 5.0),
                ('outliers', 3, 3.0), ('outliers', 4, 9.0), ('outliers', 5, 20.0)
        """)

    with Session(engine) as session:
        rows = AnaliticaRepository(session).obtener_scores_combinados_por_proveedor({
            "outliers": "outliers",
            "duplicados": "duplicados",
            "adjudicacion_directa": "directas",
        })

    assert {(row["nit_proveedor"], row["max_score_outlier"]) for row in rows} == {
        ("900123456", 5),
        ("900000002", 3),
    }
    assert {row["proveedor"] for row in rows} == {"EMPRESA HOMONIMA", "OTRO NOMBRE REPORTADO"}
    engine.dispose()
