"""Complete cut cohorts remain descriptive and cannot pretend to be stage history."""
import copy
import pytest
from modules.motor_riesgo.cut_rules import assess, TEMPORAL_SCOPE
from modules.motor_riesgo.domain import stage_time_reasons


def payload(n=31):
    rows = [{'id': i, 'fuente_id': 1, 'socrata_row_id': f'ROW{i}', 'id_del_proceso': f'P{i}',
             'id_adjudicacion': f'A{i}', 'adjudicado': 'Si', 'unit_rows_up_to_two': 1,
             'fecha_publicacion_normalizada': '2017-06-01', 'modalidad_contratacion': 'CONTRATACION DIRECTA',
             'codigo_principal_de_categoria': 'V1.80161500', 'valor_total_adjudicacion': str(i)}
            for i in range(1, n + 1)]
    return {'scope': {'temporal_scope': TEMPORAL_SCOPE, 'full_selected_cohort': True, 'raw_peer_rows': n,
                      'snapshot_cut': '2026-10-01', 'target_contract_ids': [n],
                      'selection': {'start': '2017-01-01', 'end': '2018-01-01',
                                    'method': 'CONTRATACION DIRECTA', 'category': 'V1.80161500'}}, 'rows': rows}


def test_real_reference_and_partial_coverage_remain_distinct():
    data = payload(); data['rows'][-1]['valor_total_adjudicacion'] = '1000'
    before = copy.deepcopy(data); report = assess(data)
    assert data == before and report['reference']['n'] == 31
    assert report['iqr_evaluable_targets'] == 1 and report['complete_targets'] == 0
    result = report['results'][0]
    assert result['coverage']['confirmed_signal_count'] == 1
    assert result['coverage']['complete_score'] is None
    assert result['coverage']['score_interval'] == {'min': 1, 'max': 2}
    assert result['training_eligible'] is False
    assert stage_time_reasons(result) == ['sin_reconstruccion_temporal_de_etapa']
    assert report['model_index'] is None and not report['publication_authorized']


@pytest.mark.parametrize('change', [{'raw_peer_rows': 10}, {'full_selected_cohort': False},
                                  {'temporal_scope': 'historical_stage_snapshot'}, {'target_contract_ids': [99]}])
def test_incomplete_frames_and_historical_claims_are_rejected(change):
    data = payload(); data['scope'].update(change)
    with pytest.raises(ValueError):assess(data)


@pytest.mark.parametrize('field,value', [('codigo_principal_de_categoria', 'V1.43211500'),
                                       ('modalidad_contratacion', 'LICITACION PUBLICA'),
                                       ('fecha_publicacion_normalizada', '2018-01-01')])
def test_rows_from_another_cohort_cannot_supply_peers(field, value):
    data = payload(); data['rows'][0][field] = value
    with pytest.raises(ValueError):assess(data)


@pytest.mark.parametrize('invalid', [None, 0, -1, True, 'NaN', 'Infinity'])
def test_invalid_amounts_are_excluded_without_erasing_the_target(invalid):
    data = payload(); data['rows'][-1]['valor_total_adjudicacion'] = invalid
    report = assess(data)
    assert report['reference']['n'] == 30
    assert report['reference']['exclusions']['importe_ausente_o_invalido'] == 1
    assert len(report['results']) == 1 and report['iqr_evaluable_targets'] == 0


def test_duplicates_and_ambiguous_source_units_do_not_inflate_reference():
    data = payload(33)
    data['rows'][0]['id_del_proceso'] = data['rows'][1]['id_del_proceso']
    data['rows'][0]['id_adjudicacion'] = data['rows'][1]['id_adjudicacion']
    data['rows'][2]['unit_rows_up_to_two'] = 2
    report = assess(data)
    assert report['reference']['n'] == 30
    assert report['reference']['exclusions'] == {'unidad_repetida_en_cohorte': 2, 'identidad_ambigua_o_no_comprobada': 1}


def test_small_or_constant_reference_cannot_yield_a_clear_finding():
    report = assess(payload(29))
    assert report['iqr_evaluable_targets'] == 0
    data = payload()
    for row in data['rows']:row['valor_total_adjudicacion'] = '1'
    report = assess(data)
    assert report['results'][0]['coverage']['indicators']['IMPORTE_ATIPICO']['reason'] == 'iqr_cero'


def test_reference_is_computed_once_for_all_targets_and_extras_do_not_supply_signals(monkeypatch):
    from modules.motor_riesgo import cut_rules
    original = cut_rules.iqr_finding; calls = []
    def counted(value, peers):
        calls.append(len(peers)); return original(value, peers)
    monkeypatch.setattr(cut_rules, 'iqr_finding', counted)
    data = payload(); data['scope']['target_contract_ids'] = [1, 2, 31]
    for row in data['rows']:row.update(score_final=9999, directas_90d=99)
    report = assess(data)
    assert calls == [31]
    assert all(r['coverage']['indicators']['DIRECTAS_90D']['detected'] is None for r in report['results'])


def test_offline_cli_preserves_previous_artifact(tmp_path):
    import json, subprocess, sys
    from pathlib import Path
    backend = Path(__file__).resolve().parents[1]
    source, output = tmp_path / 'input.json', tmp_path / 'report.json'
    source.write_text(json.dumps(payload()), encoding='utf-8')
    command = [sys.executable, '-I', str(backend / 'scripts/risk_cut_cohort.py'), '--input', str(source), '--output', str(output)]
    result = subprocess.run(command, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding='utf-8'))
    assert len(report['implementation_sha256']) == 6 and not report['database_accessed']
    before = output.read_bytes()
    assert subprocess.run(command, capture_output=True, timeout=20).returncode != 0
    assert output.read_bytes() == before
