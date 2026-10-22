"""Rolling evidence never turns partial history into an absence of signals."""
import copy
import pytest
from modules.motor_riesgo.rolling_evidence import assess
from modules.motor_riesgo.cut_rules import TEMPORAL_SCOPE
from modules.motor_riesgo.baseline_coverage import baseline_coverage


def frame():
    return {'scope': {'temporal_scope': TEMPORAL_SCOPE, 'raw_rows': 0,
                     'complete_pair_history': True, 'start': '2020-01-01T00:00:00-05:00',
                     'end': '2020-04-01T00:00:00-05:00'},
            'target': {'source_id': 1, 'process_id': 'TARGET', 'award_id': 'A',
                       'buyer_key': 'B', 'supplier_key': 'S', 'category': '80161500',
                       'identity_verified': True, 'award_at': '2020-04-01T00:00:00-05:00'}, 'rows': []}


def row(process='P', **changes):
    return {'source_id': 1, 'process_id': process, 'award_id': 'A',
            'buyer_key': 'B', 'supplier_key': 'S', 'category': '80161500',
            'identity_verified': True, 'award_at': '2020-03-20T00:00:00-05:00',
            'direct': True, 'method_semantics_verified': True, 'method': 'CONTRATACION DIRECTA',
            'amount': '10', 'currency': 'COP', 'justification': None, **changes}


def evaluate(rows, data=None):
    data = data or frame(); data['rows'] = rows; data['scope']['raw_rows'] = len(rows)
    return assess(data)


def test_empty_complete_frame_can_establish_zero():
    result = assess(frame())
    assert result['values'] == {'reiteraciones_30d': 0, 'directas_90d': 0}
    assert not result['training_eligible'] and not result['publication_authorized']


def test_target_process_excluded_even_when_another_award_lacks_date():
    result = evaluate([row('TARGET', award_id='OTHER', award_at=None)])
    assert result['values'] == {'reiteraciones_30d': 0, 'directas_90d': 0}
    assert result['ignored'] == {'proceso_objetivo': 1}


def test_declared_population_scope_survives_diagnostic():
    data = frame(); data['scope'].update(universe='local normalized pair', snapshot_cut='2026-10-01')
    result = assess(data)
    assert result['frame']['universe'] == 'local normalized pair'
    assert result['frame']['snapshot_cut'] == '2026-10-01'
    assert not result['frame']['coverage_outside_declared_universe_verified']


def test_windows_boundaries_future_and_target_exclusion():
    result = evaluate([row('30', award_at='2020-03-02T05:00:00+00:00'),
                       row('90', award_at='2020-01-02T00:00:00-05:00'),
                       row('OLD', award_at='2020-01-01T23:59:59-05:00'),
                       row('FUTURE', award_at='2020-04-01T00:00:01-05:00'), row('TARGET')])
    assert result['values'] == {'reiteraciones_30d': 1, 'directas_90d': 2}
    assert result['ignored'] == {'fuera_de_ventana': 1, 'evento_futuro': 1, 'proceso_objetivo': 1}


def test_awards_are_retained_but_processes_count_once_and_currency_separates():
    result = evaluate([row(), row(), row(award_id='A2', currency='USD'), row('P2')])
    direct = result['indicators']['directas_90d']
    assert direct['count'] == 2 and direct['observed_awards'] == 3
    assert direct['amounts_by_currency'] == {'COP': '20.00', 'USD': '10.00'}


def test_source_namespace_is_part_of_process_identity():
    assert evaluate([row(), row(source_id=2)])['values']['directas_90d'] == 2


@pytest.mark.parametrize('field,value', [('identity_verified', False), ('process_id', None),
                                       ('award_id', 'N/A'), ('award_at', None), ('award_at', '2020-03-20')])
def test_invalid_identity_or_time_abstains(field, value):
    result = evaluate([row(**{field: value})])
    assert all(value is None for value in result['values'].values())


def test_missing_category_only_blocks_reiteration():
    result = evaluate([row(category=None)])
    assert result['values'] == {'reiteraciones_30d': None, 'directas_90d': 1}


@pytest.mark.parametrize('changes', [{'direct': None}, {'direct': 1}, {'method_semantics_verified': False}, {'method': None}])
def test_unknown_modality_only_blocks_directas(changes):
    result = evaluate([row(**changes)])
    assert result['values'] == {'reiteraciones_30d': 1, 'directas_90d': None}


def test_30_day_history_does_not_establish_90_day_absence():
    data = frame(); data['scope']['start'] = '2020-03-01T00:00:00-05:00'
    assert assess(data)['values'] == {'reiteraciones_30d': 0, 'directas_90d': None}


@pytest.mark.parametrize('field,value', [('amount', '99'), ('method_semantics_verified', False), ('category', 'X')])
def test_conflicting_award_versions_are_not_arbitrarily_selected(field, value):
    assert evaluate([row(), row(**{field: value})])['values'] == {'reiteraciones_30d': None, 'directas_90d': None}


@pytest.mark.parametrize('changes', [{'amount': None}, {'amount': 'NaN'}, {'amount': True}, {'currency': None}, {'amount': '-1'}])
def test_amount_failure_does_not_erase_frequency(changes):
    result = evaluate([row(**changes)])
    assert result['values']['directas_90d'] == 1
    assert not result['indicators']['directas_90d']['amounts_complete']


@pytest.mark.parametrize('value', ['0.001', '1e36', '1e999999', '1e-999999', 'Infinity', '-Infinity', '0',
                                  '9' * 129])
def test_monetary_precision_and_range_never_round_invalid_awards(value):
    result = evaluate([row(amount=value)])['indicators']['directas_90d']
    assert result['count'] == 1 and result['amounts_by_currency'] == {}
    assert not result['amounts_complete']


def test_large_aggregate_keeps_cents_under_low_ambient_precision():
    from decimal import localcontext
    with localcontext() as context:
        context.prec = 6
        result = evaluate([row('LARGE', amount='123456789012345678901234567890123456.78'),
                           row('CENT', amount='0.01')])['indicators']['directas_90d']
    assert result['amounts_by_currency'] == {'COP': '123456789012345678901234567890123456.79'}
    assert result['amounts_complete']


def test_reproducible_nonmutating_and_family_capped():
    data = frame(); data['rows'] = [row(str(i)) for i in range(3)]; data['scope']['raw_rows'] = 3
    before = copy.deepcopy(data); result = assess(data)
    assert data == before and result == assess(data)
    coverage = baseline_coverage(result['values'], 'ADJUDICACION')
    assert coverage['families']['CONCENTRACION_REITERACION']['contribution'] == 1
    assert coverage['complete_score'] is None


@pytest.mark.parametrize('change', [{'temporal_scope': 'historical'}, {'raw_rows': 1}, {'complete_pair_history': 1}])
def test_invalid_scope_rejected(change):
    data = frame(); data['scope'].update(change)
    with pytest.raises(ValueError): assess(data)


def test_homonyms_cannot_join_different_identity_pairs():
    with pytest.raises(ValueError): evaluate([row(supplier_key='OTHER', supplier_name='same name')])


def test_incomplete_history_cannot_be_clear():
    data = frame(); data['scope']['complete_pair_history'] = False
    assert all(value is None for value in assess(data)['values'].values())


def test_cli_hashes_and_exclusive_output(tmp_path):
    import hashlib
    import json
    from pathlib import Path
    import subprocess
    import sys
    source, output = tmp_path / 'input.json', tmp_path / 'report.json'
    source.write_text(json.dumps(frame()), encoding='utf-8')
    cli = Path(__file__).resolve().parents[1] / 'scripts/risk_rolling_context.py'
    command = [sys.executable, str(cli), '--input', str(source), '--output', str(output)]
    subprocess.run(command, check=True, capture_output=True)
    report = json.loads(output.read_text(encoding='utf-8'))
    assert report['input_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert len(report['implementation_sha256']) == 7
    assert report['coverage']['complete_score'] is None
    before = output.read_bytes()
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert output.read_bytes() == before
