from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
import uuid
import json

from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.ingesta.model.RawSecop import RawSecop
from modules.transformacion.model.ContratoAnomaloIncompleto import ContratoAnomaloIncompleto
from modules.transformacion.model.ContratoProcesado import ContratoProcesado
from modules.transformacion.model.EstadisticaCamposFaltantes import EstadisticaCamposFaltantes
from modules.transformacion.model.ContratoAnomaliaHistorial import ContratoAnomaliaHistorial
from modules.transformacion.repository.transformacion import TransformacionRepository
from modules.transformacion.services.trasformacionservice import TransformacionService
from shared.enums import TipoFormato
from sqlalchemy import event


def test_unchanged_force_avoids_writes_but_consumes_new_source_watermarks(postgres_test_session):
    session = postgres_test_session
    source = FuenteDatos(nombre=f"pytest-watermark-{uuid.uuid4()}", tipo="TEST",
                         formato=TipoFormato.JSON, endpoint="https://example.test/watermark")
    session.add(source); session.flush()
    raw = RawSecop(fuente_id=source.id, id_del_proceso=f"watermark-{uuid.uuid4()}",
                  entidad="Entidad", nombre_del_proveedor="Proveedor",
                  valor_total_adjudicacion=Decimal("100"), tipo_de_contrato="Servicios",
                  fecha_de_publicacion_del=datetime(2025, 1, 1, tzinfo=timezone.utc),
                  sincronizado_en=datetime.now(timezone.utc) - timedelta(days=1))
    session.add(raw); session.flush(); raw_id = raw.id; session.commit()
    service = TransformacionService(session)
    assert service.process_raw_data()["procesados"] == 1
    contract = session.query(ContratoProcesado).filter_by(raw_secop_id=raw_id).one()
    original_timestamp = contract.procesado_en
    updates = []
    connection = session.get_bind()

    def observe_updates(_conn, _cursor, statement, _params, _context, _many):
        if statement.upper().startswith("UPDATE CONTRATOS_PROCESADOS "):
            updates.append(statement)

    event.listen(connection, "before_cursor_execute", observe_updates)
    try:
        unchanged = service.process_raw_data(forzar_reproceso=True)
        session.refresh(contract)
        assert unchanged["total_evaluados"] == unchanged["omitidos"] == 1
        assert unchanged["procesados"] == 0 and updates == []
        assert contract.procesado_en == original_timestamp

        # The publisher can touch a row whose normalized content is identical.
        # Its local synchronization timestamp must still become consumed.
        raw = session.get(RawSecop, raw_id)
        raw.sincronizado_en = datetime.now(timezone.utc)
        session.commit()
        refreshed_raw_at = raw.sincronizado_en
        consumed = service.process_raw_data(forzar_reproceso=True)
        session.refresh(contract)
        assert consumed["omitidos"] == 1 and len(updates) == 1
        assert contract.procesado_en >= refreshed_raw_at
        assert contract.procesado_en > original_timestamp
        assert service.process_raw_data()["total_evaluados"] == 0
        assert len(updates) == 1
        print("WATERMARK_OPTIMIZATION_EVIDENCE=" + json.dumps({
            "unchanged_forced_contract_updates": 0,
            "new_source_watermark_contract_updates": len(updates),
            "unchanged_projection_timestamp_preserved": True,
            "new_source_watermark_consumed": contract.procesado_en >= refreshed_raw_at,
            "incremental_candidates_after_consumption": 0,
            "original_projection_timestamp": original_timestamp.isoformat(),
            "refreshed_source_timestamp": refreshed_raw_at.isoformat(),
            "consumed_projection_timestamp": contract.procesado_en.isoformat(),
        }))
    finally:
        event.remove(connection, "before_cursor_execute", observe_updates)


def test_replacing_changed_anomaly_frees_unique_key_before_insert(postgres_test_session):
    session = postgres_test_session
    source = FuenteDatos(
        nombre=f"pytest-anomaly-replacement-{uuid.uuid4().hex}",
        tipo="TEST",
        formato=TipoFormato.JSON,
        endpoint="https://example.test/resource/replacement.json",
        activo=True,
    )
    session.add(source)
    session.flush()
    raw = RawSecop(
        fuente_id=source.id,
        id_del_proceso=f"pytest-replacement-{uuid.uuid4().hex}",
    )
    session.add(raw)
    session.flush()
    contract = ContratoProcesado(
        raw_secop_id=raw.id,
        id_del_proceso=raw.id_del_proceso,
        normalized_hash=uuid.uuid4().hex + uuid.uuid4().hex,
        clasificacion_riesgo="SIN_EVALUAR",
    )
    session.add(contract)
    session.flush()
    session.add(ContratoAnomaloIncompleto(
        raw_secop_id=raw.id,
        id_contrato_procesado=contract.id,
        motivo="CAMPO_FALTANTE",
        tipo_anomalia="CAMPO_FALTANTE",
        descripcion="versión anterior",
        campo_afectado="entidad",
    ))
    session.flush()

    finding = SimpleNamespace(
        raw_secop_id=raw.id,
        motivo="CAMPO_FALTANTE",
        valor_detectado="",
        tipo_anomalia="CAMPO_FALTANTE",
        valor_original=None,
        descripcion="versión actualizada",
        campo_afectado="entidad",
    )
    TransformacionRepository(session).replace_anomalias_batch(
        [(contract.id, raw.id, [finding])]
    )

    active = session.query(ContratoAnomaloIncompleto).filter_by(
        raw_secop_id=raw.id,
        campo_afectado="entidad",
    ).one()
    archived = session.query(ContratoAnomaliaHistorial).filter_by(
        raw_secop_id=raw.id,
        campo_afectado="entidad",
    ).one()
    assert active.descripcion == "versión actualizada"
    assert archived.descripcion == "versión anterior"


def test_reprocessing_reconciles_current_anomalies_and_field_counts(postgres_test_session):
    session = postgres_test_session
    source = FuenteDatos(
        nombre=f"pytest-transform-{uuid.uuid4().hex}",
        tipo="TEST",
        formato=TipoFormato.JSON,
        endpoint="https://example.test/resource/transform.json",
        activo=True,
    )
    session.add(source)
    session.flush()

    raw = RawSecop(
        fuente_id=source.id,
        id_del_proceso=f"pytest-transform-{uuid.uuid4().hex}",
        fecha_adjudicacion=datetime.now(timezone.utc) + timedelta(days=14),
    )
    session.add(raw)
    session.commit()
    raw_id = raw.id

    service = TransformacionService(session)
    first = service.process_raw_data()
    assert first["total_evaluados"] == 1
    assert first["anomalias_registradas"] == 6  # cinco obligatorios + una fecha futura
    assert session.query(ContratoAnomaloIncompleto).filter(
        ContratoAnomaloIncompleto.raw_secop_id == raw_id
    ).count() == 6
    assert session.query(EstadisticaCamposFaltantes).count() == 5

    unchanged = service.process_raw_data()
    assert unchanged["total_evaluados"] == 0
    assert session.query(ContratoAnomaloIncompleto).filter(
        ContratoAnomaloIncompleto.raw_secop_id == raw_id
    ).count() == 6

    forced_unchanged = service.process_raw_data(forzar_reproceso=True)
    assert forced_unchanged["total_evaluados"] == 1
    assert forced_unchanged["anomalias_registradas"] == 6
    assert session.query(ContratoAnomaloIncompleto).filter(
        ContratoAnomaloIncompleto.raw_secop_id == raw_id
    ).count() == 6
    assert all(
        row.contador_faltantes == 1
        for row in session.query(EstadisticaCamposFaltantes).all()
    )

    raw = session.query(RawSecop).filter(RawSecop.id == raw_id).one()
    raw.entidad = "Entidad de prueba"
    raw.nombre_del_proveedor = "Proveedor de prueba"
    raw.valor_total_adjudicacion = Decimal("125000.00")
    raw.fecha_de_publicacion_del = datetime.now(timezone.utc) - timedelta(days=30)
    raw.tipo_de_contrato = "Servicios"
    raw.fecha_adjudicacion = datetime.now(timezone.utc) - timedelta(days=2)
    session.add(raw)
    session.commit()

    repaired = service.process_raw_data(forzar_reproceso=True)
    contract = session.query(ContratoProcesado).filter(
        ContratoProcesado.raw_secop_id == raw_id
    ).one()
    assert repaired["total_evaluados"] == 1
    assert repaired["anomalias_registradas"] == 0
    assert contract.es_incompleto is False
    assert contract.es_sospechoso is False
    assert session.query(ContratoAnomaloIncompleto).filter(
        ContratoAnomaloIncompleto.raw_secop_id == raw_id
    ).count() == 0
    assert session.query(EstadisticaCamposFaltantes).count() == 0

    raw = session.query(RawSecop).filter(RawSecop.id == raw_id).one()
    raw.fecha_de_ultima_publicaci = datetime.now(timezone.utc) + timedelta(days=14)
    session.add(raw)
    session.commit()
    future = service.process_raw_data(forzar_reproceso=True)
    assert future["anomalias_registradas"] == 1
    assert session.query(ContratoProcesado).filter(
        ContratoProcesado.raw_secop_id == raw_id
    ).one().es_sospechoso is True

    raw = session.query(RawSecop).filter(RawSecop.id == raw_id).one()
    raw.fecha_de_ultima_publicaci = datetime.now(timezone.utc) - timedelta(days=1)
    session.add(raw)
    session.commit()
    corrected_date = service.process_raw_data(forzar_reproceso=True)
    assert corrected_date["anomalias_registradas"] == 0
    assert session.query(ContratoProcesado).filter(
        ContratoProcesado.raw_secop_id == raw_id
    ).one().es_sospechoso is False
    assert session.query(ContratoAnomaloIncompleto).filter(
        ContratoAnomaloIncompleto.raw_secop_id == raw_id
    ).count() == 0
