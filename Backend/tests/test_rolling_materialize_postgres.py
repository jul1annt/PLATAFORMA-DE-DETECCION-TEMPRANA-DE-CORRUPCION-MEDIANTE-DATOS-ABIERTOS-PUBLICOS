"""Parity through the actual materializer, keyset reader and observation builder."""
from collections import Counter
from datetime import datetime, timezone
import unicodedata
import pytest
from sqlalchemy import text
from test_risk_engine_postgres import source, row
from modules.motor_riesgo.domain import official_id
from modules.motor_riesgo.history import prepare_context
from modules.motor_riesgo.feature_store import fetch_batch
from modules.motor_riesgo.feature_builder import build_observation
from modules.motor_riesgo.rolling_evidence import assess
from modules.motor_riesgo.cut_rules import TEMPORAL_SCOPE
from modules.motor_riesgo.method_reference import direct_method, CONTEXT_POLICY

AT = datetime(2020, 4, 1, 5, tzinfo=timezone.utc)


def setup(db, scenario):
    src = source(db); records = []
    def add(index, process, when, *, src_item=None, category='80161500', method='CONTRATACION DIRECTA', award=None):
        raw, cp = row(db, src_item or src, index, datetime(2019, 1, 1).date(), process=process, category=category)
        raw.adjudicado = 'SI'; raw.estado_del_procedimiento = 'Seleccionado'
        raw.fecha_adjudicacion = datetime.fromisoformat(when) if when else None
        raw.id_adjudicacion = award or 'AWARD-' + str(index)
        raw.modalidad_de_contratacion = method
        cp.nit_entidad = str(src.id); cp.modalidad_contratacion = method
        records.append((raw, cp)); return raw, cp
    current, _ = add(1, 'TARGET', AT.isoformat())
    if scenario == 'empty': pass
    elif scenario == 'positive':
        for i in range(2, 5): add(i, 'P' + str(i), '2020-03-20T05:00:00+00:00')
    elif scenario == 'multiple_awards':
        add(2, 'P', '2020-03-20T05:00:00+00:00'); add(3, 'P', '2020-03-21T05:00:00+00:00')
    elif scenario == 'same_process_other_source':
        add(2, 'P', '2020-03-20T05:00:00+00:00')
        add(3, 'P', '2020-03-20T05:00:00+00:00', src_item=source(db))
    elif scenario in {'aliases', 'whitespace_aliases'}:
        add(2, 'P', '2020-03-20T05:00:00+00:00', award='A')
        add(3, ' P ' if scenario == 'whitespace_aliases' else 'P', '2020-03-20T05:00:00+00:00', award='A')
    elif scenario == 'missing_date': add(2, 'P', None)
    elif scenario == 'missing_category': add(2, 'P', '2020-03-20T05:00:00+00:00', category=None)
    elif scenario == 'missing_award':
        raw, _ = add(2, 'P', '2020-03-20T05:00:00+00:00'); raw.id_adjudicacion = None
    elif scenario == 'own_process_missing_date': add(2, 'TARGET', None)
    elif scenario == 'unknown_method': add(2, 'P', '2020-03-20T05:00:00+00:00', method='ESPECIAL INDIRECTA NO VERIFICADA')
    elif scenario == 'competitive_method': add(2, 'P', '2020-03-20T05:00:00+00:00', method='LICITACION PUBLICA')
    elif scenario == 'unicode_method':
        add(2, 'P', '2020-03-20T05:00:00+00:00', method=unicodedata.normalize('NFD', '  Contratación\tDirecta (con ofertas) '))
    elif scenario == 'boundaries':
        for i, when in enumerate(('2020-03-02T05:00:00+00:00', '2020-01-02T05:00:00+00:00',
                                  '2020-01-02T04:59:59+00:00', '2020-04-01T05:00:01+00:00'), 2):
            add(i, 'P' + str(i), when)
    else: raise AssertionError(scenario)
    db.flush()
    return current, records


def reference(current, records):
    counts = Counter((r.fuente_id, official_id(r.id_del_proceso), official_id(r.id_adjudicacion)) for r, _ in records)
    def convert(raw, cp):
        direct = direct_method(raw.modalidad_de_contratacion)
        return {'source_id': raw.fuente_id, 'process_id': raw.id_del_proceso, 'award_id': raw.id_adjudicacion,
                'buyer_key': cp.nit_entidad, 'supplier_key': cp.nit_proveedor_clave,
                'award_at': raw.fecha_adjudicacion.isoformat() if raw.fecha_adjudicacion else None,
                'identity_verified': bool(raw.socrata_row_id and official_id(raw.id_adjudicacion) and counts[
                    (raw.fuente_id, official_id(raw.id_del_proceso), official_id(raw.id_adjudicacion))] == 1),
                'category': raw.codigo_principal_de_categoria, 'direct': direct,
                'method_semantics_verified': direct is not None, 'method': raw.modalidad_de_contratacion,
                'amount': None, 'currency': None}
    rows = [convert(raw, cp) for raw, cp in records]
    target = next(row for row in rows if row['process_id'] == current.id_del_proceso and row['award_id'] == current.id_adjudicacion)
    return assess({'scope': {'temporal_scope': TEMPORAL_SCOPE, 'raw_rows': len(rows), 'complete_pair_history': True,
                             'start': '2020-01-01T00:00:00+00:00', 'end': AT.isoformat()}, 'target': target, 'rows': rows})


@pytest.mark.parametrize('scenario', ['empty', 'positive', 'multiple_awards', 'same_process_other_source',
    'aliases', 'whitespace_aliases', 'missing_date', 'missing_category', 'missing_award',
    'own_process_missing_date', 'unknown_method', 'competitive_method', 'unicode_method', 'boundaries'])
def test_materializer_counts_match_reference(postgres_test_session, scenario):
    db = postgres_test_session; current, records = setup(db, scenario)
    expected = reference(current, records)
    sources = sorted({r.fuente_id for r, _ in records})
    prepare_context(db, sources, AT.isoformat())
    actual = next(row for row in fetch_batch(db, sources, 0) if row['id'] == current.id)
    item = build_observation(actual, AT.isoformat())
    values = {name: value['value'] for name, value in item['fields'].items()}
    for name, count in expected['values'].items():
        assert values.get(name) == count, (scenario, name, values, expected)
    assert item['context']['rolling']['policy'] == CONTEXT_POLICY
    assert item['context']['directas_90d']['amount'] is None
    assert not item['context']['directas_90d']['amounts_complete']
    assert item['temporal_scope'] == 'observed_at_capture_not_backdated'
    assert not item['context']['rolling']['outside_universe_coverage_verified']


def test_ambiguous_target_does_not_receive_rolling_features(postgres_test_session):
    db = postgres_test_session; current, records = setup(db, 'positive')
    # Add a genuine second source row for the target's official award.
    from modules.ingesta.model.RawSecop import RawSecop
    from modules.transformacion.model.ContratoProcesado import ContratoProcesado
    import hashlib
    from uuid import uuid4
    alias = RawSecop(fuente_id=current.fuente_id,socrata_row_id=uuid4().hex,id_del_proceso=current.id_del_proceso,
                     id_adjudicacion=current.id_adjudicacion,adjudicado='SI',fecha_adjudicacion=AT,
                     fecha_de_publicacion_del=AT,estado_del_procedimiento='Seleccionado')
    db.add(alias);db.flush()
    db.add(ContratoProcesado(raw_secop_id=alias.id,id_del_proceso=alias.id_del_proceso,nit_entidad=str(current.fuente_id),
                            nit_proveedor_clave='900000001',normalized_hash=hashlib.sha256(uuid4().bytes).hexdigest()))
    db.flush(); prepare_context(db,[current.fuente_id],AT.isoformat())
    item=build_observation(next(r for r in fetch_batch(db,[current.fuente_id],0) if r['id']==current.id),AT.isoformat())
    assert not item['context']['rolling']['target_identity_verified']
    assert 'directas_90d' not in item['fields'] and 'reiteraciones_30d' not in item['fields']


@pytest.mark.parametrize('tz', ['America/Bogota', 'America/New_York'])
def test_materializer_boundaries_ignore_session_timezone(postgres_test_session, tz):
    db=postgres_test_session
    db.execute(text('SELECT set_config(:name,:value,true)'), {'name':'TimeZone','value':tz})
    test_materializer_counts_match_reference(db, 'boundaries')
