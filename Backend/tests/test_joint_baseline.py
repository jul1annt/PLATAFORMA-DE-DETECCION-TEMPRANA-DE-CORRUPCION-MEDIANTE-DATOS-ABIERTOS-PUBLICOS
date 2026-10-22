"""Composition checks provenance per operation without erasing independent evidence."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest
from modules.motor_riesgo.joint_baseline import assess
from test_cut_rules import payload
from test_rolling_evidence import frame, row


def inputs():
    cohort = payload()
    history = frame()
    history['scope'].update(local_contract_id=31, snapshot_cut='2026-10-01', universe='local normalized pair')
    history['target'].update(process_id='P31', award_id='A31', category='V1.80161500',
                             amount='31.00', method='CONTRATACION DIRECTA')
    return cohort, history


def test_compatible_facts_compose_and_do_not_mutate_inputs():
    cohort, history = inputs(); before = copy.deepcopy((cohort, history))
    result = assess(cohort, iter([history])); item = result['results'][0]
    assert (cohort, history) == before
    assert result['histories_accepted'] == 1 and result['complete_descriptive_counts'] == 1
    assert item['coverage']['complete_score'] == 0
    assert item['history_accepted'] and item['rolling_anchor_at']
    assert not item['database_generation_consistency_verified']
    assert not item['training_eligible'] and not item['publication_authorized']
    assert item['model_index'] is None and not result['training_eligible']
    assert result == assess(cohort, [history])


def test_absent_history_never_becomes_zero():
    cohort, _ = inputs(); item = assess(cohort, [])['results'][0]
    assert item['coverage']['families']['IMPORTE_ATIPICO']['status'] == 'SIN_SENAL'
    assert item['coverage']['families']['CONCENTRACION_REITERACION']['status'] == 'NO_EVALUABLE'
    assert item['coverage']['complete_score'] is None
    assert item['history_abstention_reason'] == 'sin_historia_comprobada'


@pytest.mark.parametrize('field,value,reason', [
    ('source_id', 2, 'identidad_operacion_incompatible'),
    ('source_id', True, 'identidad_operacion_incompatible'),
    ('process_id', 'P30', 'identidad_operacion_incompatible'),
    ('award_id', 'OTHER', 'identidad_operacion_incompatible'),
    ('identity_verified', False, 'identidad_historia_no_admisible'),
    ('category', '80161500', 'categoria_objetivo_incompatible'),
    ('method', 'LICITACION PUBLICA', 'modalidad_objetivo_incompatible'),
    ('amount', '32', 'importe_objetivo_incompatible'),
    ('amount', True, 'importe_objetivo_incompatible'),
    ('award_at', '2016-01-01T00:00:00Z', 'adjudicacion_anterior_a_publicacion'),
    ('award_at', '2026-10-02T05:00:00Z', 'adjudicacion_posterior_al_corte'),
    ('award_at', None, 'fecha_objetivo_no_admisible')])
def test_mismatched_history_abstains_without_erasing_iqr(field, value, reason):
    cohort, history = inputs(); history['target'][field] = value
    result = assess(cohort, [history]); item = result['results'][0]
    assert result['histories_accepted'] == 0 and item['history_abstention_reason'] == reason
    assert item['coverage']['families']['IMPORTE_ATIPICO']['status'] == 'SIN_SENAL'
    assert item['coverage']['complete_score'] is None


@pytest.mark.parametrize('change,reason', [({'snapshot_cut': '2026-10-02'}, 'corte_incompatible'),
    ({'temporal_scope': 'historical'}, 'alcance_o_etapa_incompatible'),
    ({'stage': 'CONVOCATORIA'}, 'alcance_o_etapa_incompatible')])
def test_cut_stage_and_temporal_scope_are_not_mixed(change, reason):
    cohort, history = inputs(); history['scope'].update(change)
    assert assess(cohort, [history])['results'][0]['history_abstention_reason'] == reason


@pytest.mark.parametrize('field,value', [('unit_rows_up_to_two', 2), ('unit_rows_up_to_two', True),
                                        ('socrata_row_id', None), ('adjudicado', 'NO')])
def test_invalid_cohort_identity_or_award_does_not_accept_context(field, value):
    cohort, history = inputs(); cohort['rows'][-1][field] = value
    result = assess(cohort, [history])
    assert result['histories_accepted'] == 0


def test_repeated_official_unit_cannot_accept_context():
    cohort, history = inputs()
    cohort['rows'][0].update(id_del_proceso='P31', id_adjudicacion='A31')
    assert assess(cohort, [history])['results'][0]['history_abstention_reason'] == 'unidad_repetida_en_cohorte'


def test_bad_amount_does_not_erase_usable_windows():
    cohort, history = inputs(); cohort['rows'][-1]['valor_total_adjudicacion'] = None
    history['target']['amount'] = None
    item = assess(cohort, [history])['results'][0]
    assert item['history_accepted']
    assert item['coverage']['families']['IMPORTE_ATIPICO']['status'] == 'NO_EVALUABLE'
    assert item['coverage']['families']['CONCENTRACION_REITERACION']['status'] == 'SIN_SENAL'


def test_two_rolling_signals_count_one_family_and_competition_stays_unknown():
    cohort, history = inputs(); method = 'CONTRATACIÓN DIRECTA (CON OFERTAS)'
    cohort['scope']['selection']['method'] = method
    for record in cohort['rows']: record['modalidad_contratacion'] = method
    cohort['rows'][-1]['valor_total_adjudicacion'] = '1000'
    history['target'].update(method=method, amount='1000')
    history['rows'] = [row(str(i), category='V1.80161500') for i in range(3)]
    history['scope']['raw_rows'] = 3
    item = assess(cohort, [history])['results'][0]
    assert item['coverage']['confirmed_signal_count'] == 2
    assert item['coverage']['families']['CONCENTRACION_REITERACION']['contribution'] == 1
    assert item['coverage']['families']['COMPETENCIA']['status'] == 'NO_EVALUABLE'
    assert item['coverage']['complete_score'] is None
    assert item['coverage']['score_interval'] == {'min': 2, 'max': 3}


def test_magnitude_cannot_dominate_binary_family_weight():
    cohort, history = inputs(); scores = []
    for amount in ('1000', '1000000000000000000000000000000'):
        cohort['rows'][-1]['valor_total_adjudicacion'] = amount; history['target']['amount'] = amount
        item = assess(cohort, [history])['results'][0]
        scores.append(item['coverage']['families']['IMPORTE_ATIPICO']['contribution'])
    assert scores == [1, 1]


def test_legacy_supplier_scores_are_not_operation_features():
    cohort, history = inputs(); before = assess(cohort, [history])['results'][0]['coverage']
    cohort['rows'][-1]['score_riesgo'] = '9999999999'
    history['target']['score_final'] = '9999999999'
    assert assess(cohort, [history])['results'][0]['coverage'] == before


@pytest.mark.parametrize('kind', ['duplicate', 'unselected', 'orphan'])
def test_no_arbitrary_choice_of_history_target(kind):
    cohort, history = inputs(); histories = [history]
    if kind == 'duplicate': histories.append(copy.deepcopy(history))
    else: history['scope']['local_contract_id'] = 30 if kind == 'unselected' else 999
    with pytest.raises(ValueError): assess(cohort, histories)


def test_broken_history_keeps_iqr_and_records_abstention():
    cohort, history = inputs(); del history['rows']
    item = assess(cohort, [history])['results'][0]
    assert item['history_abstention_reason'] == 'historia_no_admisible'
    assert item['coverage']['families']['IMPORTE_ATIPICO']['status'] == 'SIN_SENAL'


def test_cli_frozen_inputs_no_overwrite_and_hash_guard(tmp_path):
    cohort, history = inputs(); entries = []
    for name, data in [('cohort.json', cohort), ('history.json', history)]:
        path = tmp_path / name; path.write_text(json.dumps(data), encoding='utf-8')
        entries.append({'path': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'version': 'joint-baseline-input-v1', 'cohort': entries[0], 'histories': entries[1:]}))
    output = tmp_path / 'report.json'; script = Path(__file__).resolve().parents[1] / 'scripts/risk_joint_baseline.py'
    command = [sys.executable, '-I', '-S', str(script), '--manifest', str(manifest), '--output', str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding='utf-8'))
    assert len(report['input_files']) == 2 and len(report['implementation_sha256']) == 9
    assert report['priority_analysis']['policy'] == 'coverage-and-weight-robust-priority-v1'
    assert all('priority' in row for row in report['results'])
    before = output.read_bytes()
    assert subprocess.run(command, capture_output=True).returncode != 0 and output.read_bytes() == before
    (tmp_path / 'history.json').write_text('{}')
    command[-1] = str(tmp_path / 'other.json')
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert not (tmp_path / 'other.json').exists()
