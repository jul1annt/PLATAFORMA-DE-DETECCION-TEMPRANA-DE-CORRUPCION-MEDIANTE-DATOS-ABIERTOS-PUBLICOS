from datetime import datetime, timezone
from sqlalchemy.dialects import postgresql

from modules.transformacion.model.ContratoAnomaloIncompleto import ContratoAnomaloIncompleto
from modules.transformacion.model.ContratoAnomaliaHistorial import ContratoAnomaliaHistorial
from modules.transformacion.repository.transformacion import TransformacionRepository
from modules.transformacion.services.normalization_service import AnomalyFinding


def test_save_all_contracts_flushes_without_committing_the_callers_transaction():
    class Session:
        commits = 0
        flushes = 0

        def add_all(self, rows):
            self.rows = rows

        def flush(self):
            self.flushes += 1

        def commit(self):
            self.commits += 1

    session = Session()
    rows = [object()]

    TransformacionRepository(session).save_all_contratos(rows)

    assert session.rows is rows
    assert session.flushes == 1
    assert session.commits == 0


def test_missing_field_reconciliation_counts_legacy_and_current_anomaly_types():
    compiled = TransformacionRepository._criterio_campo_faltante().compile(
        dialect=postgresql.dialect()
    )
    sql = str(compiled)

    assert "coalesce(contrato_anomalo_incompleto.tipo_anomalia" in sql
    assert "contrato_anomalo_incompleto.motivo)" in sql
    assert "CAMPO_FALTANTE" in compiled.params.values()


def test_repository_materializes_pure_anomaly_finding_at_persistence_boundary():
    finding = AnomalyFinding(
        raw_secop_id=31,
        motivo="MONTO_NEGATIVO",
        valor_detectado="-5",
        tipo_anomalia="MONTO_NEGATIVO",
        valor_original="-5",
        descripcion="Monto de origen negativo",
        campo_afectado="precio_base",
    )

    entity = TransformacionRepository._materializar_anomalia(finding, contrato_id=88)

    assert entity.raw_secop_id == 31
    assert entity.id_contrato_procesado == 88
    assert entity.tipo_anomalia == "MONTO_NEGATIVO"
    assert entity.valor_original == "-5"
    assert entity.campo_afectado == "precio_base"


def test_save_anomalies_attaches_contract_id_without_mutating_immutable_findings():
    finding = _finding()

    class Session:
        def add_all(self, rows):
            self.rows = rows

        def flush(self):
            self.flushed = True

    session = Session()
    TransformacionRepository(session).save_all_anomalias([finding], contrato_id=88)

    assert session.rows[0].id_contrato_procesado == 88
    assert finding.raw_secop_id == 31
    assert session.flushed is True


class _AnomalySession:
    def __init__(self, current):
        self.current = current
        self.added = []
        self.deleted = []
        self.flushes = 0

    def query(self, _model):
        session = self

        class Query:
            def filter(self, *_args):
                return self

            def all(self):
                return session.current

        return Query()

    def add(self, item):
        self.added.append(item)

    def add_all(self, items):
        self.added.extend(items)

    def delete(self, item):
        self.deleted.append(item)

    def flush(self):
        self.flushes += 1


def _finding(value="-5"):
    return AnomalyFinding(
        raw_secop_id=31,
        motivo="MONTO_NEGATIVO",
        valor_detectado=value,
        tipo_anomalia="MONTO_NEGATIVO",
        valor_original=value,
        descripcion="Monto de origen negativo",
        campo_afectado="precio_base",
    )


def _active_anomaly(value="-5"):
    return ContratoAnomaloIncompleto(
        id=14,
        raw_secop_id=31,
        id_contrato_procesado=88,
        motivo="MONTO_NEGATIVO",
        valor_detectado=value,
        tipo_anomalia="MONTO_NEGATIVO",
        valor_original=value,
        descripcion="Monto de origen negativo",
        campo_afectado="precio_base",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_reconciliation_preserves_unchanged_active_anomaly_without_history():
    existing = _active_anomaly()
    session = _AnomalySession([existing])

    TransformacionRepository(session).replace_anomalias(88, [_finding()], raw_secop_id=31)

    assert session.deleted == []
    assert session.added == []
    assert session.flushes == 1


def test_reconciliation_repairs_legacy_active_anomaly_contract_link():
    existing = _active_anomaly()
    existing.id_contrato_procesado = None
    session = _AnomalySession([existing])

    TransformacionRepository(session).replace_anomalias(
        88,
        [_finding()],
        raw_secop_id=31,
    )

    assert existing.id_contrato_procesado == 88
    assert session.deleted == []
    assert session.added == []


def test_reconciliation_archives_changed_anomaly_and_inserts_current_version():
    existing = _active_anomaly()
    session = _AnomalySession([existing])

    TransformacionRepository(session).replace_anomalias(88, [_finding("-8")], raw_secop_id=31)

    assert session.deleted == [existing]
    history = next(row for row in session.added if isinstance(row, ContratoAnomaliaHistorial))
    current = next(row for row in session.added if isinstance(row, ContratoAnomaloIncompleto))
    assert history.anomalia_id_original == 14
    assert history.valor_original == "-5"
    assert history.fecha_inicio == existing.created_at
    assert history.fecha_fin.tzinfo is not None
    assert current.valor_original == "-8"
    assert current.id_contrato_procesado == 88


def test_reconciliation_archives_anomaly_when_it_is_resolved():
    existing = _active_anomaly()
    session = _AnomalySession([existing])

    TransformacionRepository(session).replace_anomalias(88, [], raw_secop_id=31)

    assert session.deleted == [existing]
    assert len(session.added) == 1
    assert isinstance(session.added[0], ContratoAnomaliaHistorial)


def test_new_contract_anomalies_are_inserted_without_reading_old_findings():
    class NewContractSession(_AnomalySession):
        def query(self, _model):
            raise AssertionError("A newly inserted contract has no findings to read")

    session = NewContractSession([])

    TransformacionRepository(session).replace_anomalias_batch(
        [(88, 31, [_finding()])],
        nuevos_raw_ids={31},
    )

    assert session.deleted == []
    assert session.flushes == 1
    assert len(session.added) == 1
    assert isinstance(session.added[0], ContratoAnomaloIncompleto)
    assert session.added[0].id_contrato_procesado == 88
