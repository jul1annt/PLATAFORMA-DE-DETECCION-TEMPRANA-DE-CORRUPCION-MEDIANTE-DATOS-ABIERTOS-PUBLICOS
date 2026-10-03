"""PostgreSQL integration coverage for source-driven raw-row versioning."""

from __future__ import annotations

import uuid
from decimal import Decimal

from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.ingesta.model.RawSecop import RawSecop
from modules.ingesta.model.RawSecopHistorial import RawSecopHistorial
from modules.ingesta.repository.IngestaRepository import IngestaRepository
from shared.enums import TipoFormato


def test_changed_upsert_archives_previous_snapshot_once(postgres_test_session):
    db = postgres_test_session
    source = FuenteDatos(
        nombre=f"raw-history-{uuid.uuid4().hex[:20]}",
        tipo="SECOP",
        formato=TipoFormato.JSON,
        endpoint="https://www.datos.gov.co/resource/test.json",
    )
    db.add(source)
    db.flush()

    repository = IngestaRepository(db)
    process_id = f"history-{uuid.uuid4().hex}"
    assert repository.insertar_raw_secop_bulk(
        [{"id_del_proceso": process_id, "nombre_del_procedimiento": "versión inicial"}],
        source.id,
    ) == 1

    assert repository.insertar_raw_secop_bulk(
        [{"id_del_proceso": process_id, "nombre_del_procedimiento": "versión actualizada"}],
        source.id,
    ) == 0

    history = db.query(RawSecopHistorial).filter(
        RawSecopHistorial.id_del_proceso == process_id
    ).all()
    current = db.query(RawSecop).filter(RawSecop.id_del_proceso == process_id).one()
    assert len(history) == 1
    assert history[0].fuente_id == source.id
    assert history[0].datos_anteriores["nombre_del_procedimiento"] == "versión inicial"
    assert current.nombre_del_procedimiento == "versión actualizada"

    # Re-reading an identical source row must not create another history entry.
    repository.insertar_raw_secop_bulk(
        [{"id_del_proceso": process_id, "nombre_del_procedimiento": "versión actualizada"}],
        source.id,
    )
    assert db.query(RawSecopHistorial).filter(
        RawSecopHistorial.id_del_proceso == process_id
    ).count() == 1


def test_bulk_upsert_preserves_distinct_awards_and_updates_same_socrata_row(
    postgres_test_session,
):
    db = postgres_test_session
    source = FuenteDatos(
        nombre=f"raw-batch-dedupe-{uuid.uuid4().hex[:16]}",
        tipo="SECOP",
        formato=TipoFormato.JSON,
        endpoint="https://www.datos.gov.co/resource/test.json",
    )
    db.add(source)
    db.flush()

    process_id = f"batch-dedupe-{uuid.uuid4().hex}"
    inserted = IngestaRepository(db).insertar_raw_secop_bulk(
        [
            {
                "id_del_proceso": process_id,
                "nombre_del_proveedor": "Proveedor A antiguo",
                "nit_del_proveedor_adjudicado": "900111222",
                "valor_total_adjudicacion": 100,
                ":updated_at": "2026-09-28T10:00:00.000",
                ":id": "award-a",
            },
            {
                "id_del_proceso": process_id,
                "nombre_del_proveedor": "Proveedor B",
                "nit_del_proveedor_adjudicado": "900333444",
                "valor_total_adjudicacion": 200,
                ":updated_at": "2026-09-29T10:00:00.000",
                ":id": "award-b",
            },
            {
                "id_del_proceso": process_id,
                "nombre_del_proveedor": "Proveedor A reciente",
                "nit_del_proveedor_adjudicado": "900111222",
                "valor_total_adjudicacion": 125,
                ":updated_at": "2026-09-28T12:00:00.000",
                ":id": "award-a",
            },
        ],
        source.id,
    )

    rows = db.query(RawSecop).filter(RawSecop.id_del_proceso == process_id).all()
    rows_by_id = {row.socrata_row_id: row for row in rows}
    assert inserted == 2
    assert len(rows) == 2
    assert rows_by_id["award-a"].nombre_del_proveedor == "Proveedor A reciente"
    assert rows_by_id["award-a"].valor_total_adjudicacion == 125
    assert rows_by_id["award-b"].nombre_del_proveedor == "Proveedor B"


def test_bulk_upsert_splits_large_socrata_page_into_safe_insert_batches(postgres_test_session):
    db = postgres_test_session
    source = FuenteDatos(
        nombre=f"raw-batch-500-{uuid.uuid4().hex[:16]}",
        tipo="SECOP",
        formato=TipoFormato.JSON,
        endpoint="https://www.datos.gov.co/resource/test.json",
    )
    db.add(source)
    db.flush()

    process_id = f"batch-500-{uuid.uuid4().hex}"
    records = [
        {
            "id_del_proceso": process_id,
            "nombre_del_proveedor": f"Proveedor {index}",
            "valor_total_adjudicacion": (
                Decimal("1234567890123456789.00") if index == 0 else None
            ),
            ":id": f"award-{index}",
        }
        for index in range(5000)
    ]
    inserted = IngestaRepository(db).insertar_raw_secop_bulk(records, source.id)

    assert inserted == 5000
    assert db.query(RawSecop).filter(RawSecop.id_del_proceso == process_id).count() == 5000
    oversized = db.query(RawSecop).filter(RawSecop.socrata_row_id == "award-0").one()
    assert oversized.valor_total_adjudicacion == Decimal("1234567890123456789.00")


def test_bulk_upsert_treats_blank_process_ids_as_missing(postgres_test_session):
    db = postgres_test_session
    source = FuenteDatos(
        nombre=f"raw-batch-null-id-{uuid.uuid4().hex[:16]}",
        tipo="SECOP",
        formato=TipoFormato.JSON,
        endpoint="https://www.datos.gov.co/resource/test.json",
    )
    db.add(source)
    db.flush()

    repository = IngestaRepository(db)
    inserted = repository.insertar_raw_secop_bulk(
        [
            {"id_del_proceso": "", "nombre_del_procedimiento": "sin id 1"},
            {"id_del_proceso": "   ", "nombre_del_procedimiento": "sin id 2"},
        ],
        source.id,
    )
    rows = db.query(RawSecop).filter(
        RawSecop.fuente_id == source.id
    ).all()
    assert inserted == 2
    assert len(rows) == 2
    assert all(row.id_del_proceso is None for row in rows)
