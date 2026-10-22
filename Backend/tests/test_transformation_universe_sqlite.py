from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from modules.transformacion.repository.transformacion import TransformacionRepository


def test_default_processing_universe_includes_new_and_source_modified_rows():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE raw_secop (id INTEGER PRIMARY KEY, sincronizado_en DATETIME)"
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE contratos_procesados (
                id INTEGER PRIMARY KEY,
                raw_secop_id INTEGER,
                procesado_en DATETIME
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO raw_secop (id, sincronizado_en) VALUES
                (1, '2026-01-01 00:00:00.000000'),
                (2, '2026-01-02 00:00:00.000000'),
                (3, '2026-01-01 00:00:00.000000'),
                (4, '2026-01-01 00:00:00.000000')
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO contratos_procesados (id, raw_secop_id, procesado_en) VALUES
                (1, 1, '2026-01-01 00:00:00.000000'),
                (2, 2, '2026-01-01 00:00:00.000000'),
                (3, 4, '2026-01-02 00:00:00.000000')
            """
        )

    try:
        with Session(engine) as session:
            repository = TransformacionRepository(session)
            incremental = repository.obtener_universo_reprocesamiento(False)
            forced = repository.obtener_universo_reprocesamiento(True)

        assert incremental == {
            "max_raw_secop_id": 4,
            "total_candidatos": 2,
            "forzar_reproceso": False,
        }
        assert forced == {
            "max_raw_secop_id": 4,
            "total_candidatos": 4,
            "forzar_reproceso": True,
        }
    finally:
        engine.dispose()
