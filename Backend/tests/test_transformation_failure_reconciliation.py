from types import SimpleNamespace

import pytest

from modules.transformacion.model.ProcesamientoLog import ProcesamientoLog
from modules.transformacion.model.ContratoProcesado import ContratoProcesado
from modules.transformacion.services.normalization_service import AnomalyFinding
from modules.transformacion.services.trasformacionservice import TransformacionService


def test_empty_candidate_universe_does_not_repeat_the_full_row_query():
    class Session:
        def __init__(self):
            self.logs = []

        def add(self, item):
            self.logs.append(item)

        def commit(self):
            pass

        def rollback(self):
            pass

        def query(self, *_args, **_kwargs):
            raise AssertionError("an empty universe must not scan raw rows again")

    session = Session()
    service = TransformacionService(session)
    service.repo.obtener_universo_reprocesamiento = lambda _force: {
        "max_raw_secop_id": 9249545, "total_candidatos": 0, "forzar_reproceso": False,
    }
    statistics = []
    service.repo.recalculate_porcentajes_estadisticas_campos = lambda: statistics.append(True)
    result = service.process_raw_data(job_id=73)
    assert result["estado"] == "EXITOSO"
    assert result["total_evaluados"] == result["procesados"] == 0
    log = session.logs[-1]
    assert log.estado == "EXITOSO" and log.universo["total_candidatos"] == 0
    assert log.universo["background_job_id"] == 73
    assert log.universo["candidatos_verificados_en"]
    assert statistics == [True]


@pytest.mark.parametrize("failure_point", ["query", "normalization", "commit"])
def test_failed_reprocessing_rebuilds_field_statistics_from_committed_chunks(failure_point):
    raw = SimpleNamespace(id=1)
    next_raw = SimpleNamespace(id=2)

    class Query:
        calls = 0

        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def all(self):
            self.calls += 1
            if self.calls == 1:
                return [raw]
            if failure_point == "query":
                raise RuntimeError("simulated failure after first committed chunk")
            return [next_raw] if self.calls == 2 else []

    class Session:
        def __init__(self):
            self.query_result = Query()
            self.added = []
            self.commits = 0
            self.rollbacks = 0

        def add(self, item):
            self.added.append(item)

        def query(self, *_args, **_kwargs):
            return self.query_result

        def flush(self):
            for item in self.added:
                if isinstance(item, ContratoProcesado) and item.id is None:
                    item.id = 77

        def commit(self):
            self.commits += 1
            if failure_point == "commit" and self.commits == 4:
                raise RuntimeError("simulated failure committing second chunk")

        def rollback(self):
            self.rollbacks += 1

        def expunge(self, _item):
            pass

    session = Session()
    service = TransformacionService(session)
    service.repo.obtener_universo_reprocesamiento = lambda _force: {
        "max_raw_secop_id": 2,
        "total_candidatos": 2,
        "forzar_reproceso": True,
    }
    def normalize(record):
        if failure_point == "normalization" and record.id == 2:
            raise RuntimeError("simulated failure during second chunk")
        return {"raw_secop_id": record.id}

    service._normalizar = normalize
    service._detectar_anomalias = lambda _record: []
    reconciliations = []
    service.repo.obtener_contratos_por_raw_ids = lambda _raw_ids: {}
    service.repo.replace_anomalias_batch = lambda _replacements, **_kwargs: None
    service.repo.recalculate_porcentajes_estadisticas_campos = lambda: reconciliations.append(True)

    with pytest.raises(RuntimeError, match="simulated failure"):
        service.process_raw_data(forzar_reproceso=True)

    assert reconciliations == [True]
    assert session.rollbacks == 1
    assert session.commits == (6 if failure_point == "commit" else 5)
    failed_log = next(item for item in session.added if isinstance(item, ProcesamientoLog))
    assert failed_log.estado == "ERROR"
    assert failed_log.version_reglas == "v1.0"
    assert failed_log.universo["total_candidatos"] == 2
    assert failed_log.universo["total_evaluados"] == 1
    assert failed_log.universo["ultimo_raw_secop_id"] == 1
    assert failed_log.total_evaluados == failed_log.procesados == 1


def test_successful_reprocessing_records_rule_version_and_fixed_universe():
    raw = SimpleNamespace(id=7)

    class Query:
        calls = 0

        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def all(self):
            self.calls += 1
            return [raw] if self.calls == 1 else []

    class Session:
        def __init__(self):
            self.query_result = Query()
            self.added = []

        def add(self, item):
            self.added.append(item)

        def query(self, *_args, **_kwargs):
            return self.query_result

        def flush(self):
            for item in self.added:
                if isinstance(item, ContratoProcesado) and item.id is None:
                    item.id = 77

        def commit(self):
            pass

        def expunge(self, _item):
            pass

    session = Session()
    service = TransformacionService(session)
    service.repo.obtener_universo_reprocesamiento = lambda _force: {
        "max_raw_secop_id": 9,
        "total_candidatos": 2,
        "forzar_reproceso": True,
    }
    service._normalizar = lambda record: {"raw_secop_id": record.id}
    finding = AnomalyFinding(
        raw_secop_id=7,
        motivo="CAMPO_FALTANTE",
        valor_detectado=None,
        tipo_anomalia="CAMPO_FALTANTE",
        valor_original=None,
        descripcion="Falta entidad",
        campo_afectado="entidad",
    )
    service._detectar_anomalias = lambda _record: [finding]
    service.repo.obtener_contratos_por_raw_ids = lambda _raw_ids: {}
    saved_contract_ids = []
    service.repo.replace_anomalias_batch = lambda replacements, **_kwargs: saved_contract_ids.extend(
        contrato_id for contrato_id, _raw_id, _hallazgos in replacements
    )
    service.repo.recalculate_porcentajes_estadisticas_campos = lambda: None

    result = service.process_raw_data(forzar_reproceso=True)

    success_log = next(item for item in session.added if isinstance(item, ProcesamientoLog))
    assert result["estado"] == success_log.estado == "EXITOSO"
    assert success_log.version_reglas == "v1.0"
    assert success_log.universo["max_raw_secop_id"] == 9
    assert success_log.universo["total_candidatos"] == 2
    assert success_log.universo["total_evaluados"] == 1
    assert success_log.universo["ultimo_raw_secop_id"] == 7
    assert result["anomalias_registradas"] == 1
    assert saved_contract_ids == [77]


def test_reprocessing_loads_and_reconciles_contracts_per_chunk():
    raws = [SimpleNamespace(id=7), SimpleNamespace(id=8)]

    class Query:
        calls = 0

        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def all(self):
            self.calls += 1
            return raws if self.calls == 1 else []

    class Session:
        def __init__(self):
            self.query_result = Query()
            self.added = []
            self.flush_calls = 0

        def add(self, item):
            self.added.append(item)

        def query(self, *_args, **_kwargs):
            return self.query_result

        def flush(self):
            self.flush_calls += 1
            next_id = 77
            for item in self.added:
                if isinstance(item, ContratoProcesado) and item.id is None:
                    item.id = next_id
                    next_id += 1

        def commit(self):
            pass

        def expunge(self, _item):
            pass

    session = Session()
    service = TransformacionService(session)
    service.repo.obtener_universo_reprocesamiento = lambda _force: {
        "max_raw_secop_id": 8,
        "total_candidatos": 2,
        "forzar_reproceso": True,
    }
    service._normalizar = lambda record: {"raw_secop_id": record.id}
    service._detectar_anomalias = lambda _record: []
    looked_up = []
    service.repo.obtener_contratos_por_raw_ids = lambda raw_ids: (
        looked_up.append(raw_ids) or {}
    )
    reconciled = []
    service.repo.replace_anomalias_batch = lambda replacements, **_kwargs: reconciled.append(
        replacements
    )
    service.repo.recalculate_porcentajes_estadisticas_campos = lambda: None

    result = service.process_raw_data(forzar_reproceso=True)

    assert result["total_evaluados"] == 2
    assert result["procesados"] == 2
    assert looked_up == [[7, 8]]
    assert len(reconciled) == 1
    assert [(contract_id, raw_id) for contract_id, raw_id, _ in reconciled[0]] == [
        (77, 7), (78, 8)
    ]
    assert session.flush_calls == 1
