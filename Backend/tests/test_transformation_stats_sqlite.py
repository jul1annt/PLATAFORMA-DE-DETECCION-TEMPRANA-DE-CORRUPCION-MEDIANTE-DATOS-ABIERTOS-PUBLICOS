from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from modules.transformacion.model.EstadisticaCamposFaltantes import EstadisticaCamposFaltantes
from modules.transformacion.repository.transformacion import TransformacionRepository


def test_field_statistics_rebuild_counts_legacy_anomalies_and_all_processed_contracts():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE contratos_procesados (id INTEGER PRIMARY KEY, raw_secop_id INTEGER NOT NULL)"
        ))
        connection.execute(text("""
            CREATE TABLE contrato_anomalo_incompleto (
                id INTEGER PRIMARY KEY,
                campo_afectado VARCHAR(100) NOT NULL,
                tipo_anomalia VARCHAR(50),
                motivo VARCHAR(50)
            )
        """))
        connection.execute(text("""
            CREATE TABLE estadistica_campos_faltantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_campo VARCHAR(100) NOT NULL UNIQUE,
                contador_faltantes INTEGER NOT NULL,
                porcentaje_total NUMERIC(5, 2),
                updated_at DATETIME
            )
        """))
        connection.execute(text(
            "INSERT INTO contratos_procesados (id, raw_secop_id) VALUES (1, 10), (2, 20), (3, 30), (4, 40)"
        ))
        connection.execute(text("""
            INSERT INTO contrato_anomalo_incompleto
                (id, campo_afectado, tipo_anomalia, motivo)
            VALUES
                (1, 'entidad', 'CAMPO_FALTANTE', 'CAMPO_FALTANTE'),
                (2, 'entidad', NULL, 'CAMPO_FALTANTE'),
                (3, 'entidad', 'MONTO_NEGATIVO', 'MONTO_NEGATIVO'),
                (4, 'proveedor', 'CAMPO_FALTANTE', 'CAMPO_FALTANTE')
        """))
        connection.execute(text("""
            INSERT INTO estadistica_campos_faltantes
                (nombre_campo, contador_faltantes, porcentaje_total)
            VALUES ('obsoleto', 99, 999.0)
        """))

    with Session(engine) as session:
        TransformacionRepository(session).recalculate_porcentajes_estadisticas_campos()
        session.commit()
        stats = {
            row.nombre_campo: (row.contador_faltantes, float(row.porcentaje_total))
            for row in session.query(EstadisticaCamposFaltantes).all()
        }

    assert stats == {"entidad": (2, 50.0), "proveedor": (1, 25.0)}
    engine.dispose()
