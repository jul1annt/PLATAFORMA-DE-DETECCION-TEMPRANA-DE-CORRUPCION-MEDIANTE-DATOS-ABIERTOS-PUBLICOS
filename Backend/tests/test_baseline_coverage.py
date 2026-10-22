"""Synthetic checks of signal semantics; never judicial validation."""
from math import log1p
import pytest
from modules.motor_riesgo.baseline_coverage import baseline_coverage
from modules.motor_riesgo.rules import chronological_baseline, iqr_finding, iqr_finding_from_reference, iqr_reference


def values(**changes):
    return {'modalidad': 'Contratación directa', 'directas_90d': 0,
            'reiteraciones_30d': 0, **changes}


def test_unknowns_have_an_interval_and_do_not_become_a_complete_zero():
    result = baseline_coverage({}, 'ADJUDICACION')
    assert result['complete_score'] is None
    assert result['score_interval'] == {'min': 0, 'max': 3}
    assert result['evaluated_families'] == 0 and result['family_coverage'] == 0
    assert result['publication_authorized'] is False


def test_call_does_not_use_future_award_features():
    result = baseline_coverage(values(oferentes=1, directas_90d=99), 'CONVOCATORIA', {'detected': False})
    assert result['complete_score'] == 0 and result['family_coverage'] == 1
    assert result['applicable_families'] == 1
    assert result['indicators']['OFERENTE_UNICO']['status'] == 'NO_APLICA'


@pytest.mark.parametrize('field', ['directas_90d', 'reiteraciones_30d'])
@pytest.mark.parametrize('invalid', [None, -1, float('nan'), float('inf'), True, .5, 'bad'])
def test_missing_or_invalid_history_is_not_evaluated_as_zero(field, invalid):
    result = baseline_coverage(values(**{field: invalid}), 'ADJUDICACION', {'detected': False})
    assert result['indicators']['DIRECTAS_90D' if field == 'directas_90d' else 'REITERACION_30D']['detected'] is None
    assert result['complete_score'] is None
    assert result['score_interval'] == {'min': 0, 'max': 1}


def test_correlated_signals_contribute_one_family_and_keep_indicator_coverage():
    result = baseline_coverage(values(directas_90d=4, reiteraciones_30d=3), 'ADJUDICACION', {'detected': False})
    assert result['confirmed_signal_count'] == 1 and result['complete_score'] == 1
    result = baseline_coverage(values(directas_90d=4, reiteraciones_30d=None), 'ADJUDICACION', {'detected': False})
    assert result['complete_score'] == 1
    assert result['evaluated_indicators'] == 2 and result['applicable_indicators'] == 3
    assert result['indicators']['REITERACION_30D']['status'] == 'NO_EVALUABLE'


def test_competition_requires_verified_dictionary_and_explicit_modality():
    result = baseline_coverage(values(modalidad='Licitación pública', oferentes=1), 'ADJUDICACION', {'detected': False})
    assert result['indicators']['OFERENTE_UNICO']['reason'] == 'semantica_oferentes_no_verificada'
    assert result['complete_score'] is None
    verified = baseline_coverage(values(modalidad='Licitación pública', oferentes=1), 'ADJUDICACION',
                                 {'detected': False}, competition_semantics_verified=True)
    assert verified['complete_score'] == 1
    unknown = baseline_coverage(values(modalidad='seleccion misteriosa', oferentes=1), 'ADJUDICACION',
                                {'detected': False}, competition_semantics_verified=True)
    assert unknown['indicators']['OFERENTE_UNICO']['reason'] == 'modalidad_no_verificada'


@pytest.mark.parametrize('invalid', [0, True, -1, float('inf'), 1.5, None])
def test_invalid_bidder_count_cannot_be_a_clear_competition_finding(invalid):
    result = baseline_coverage(values(modalidad='Licitación pública', oferentes=invalid), 'ADJUDICACION',
                               {'detected': False}, competition_semantics_verified=True)
    assert result['indicators']['OFERENTE_UNICO']['detected'] is None


@pytest.mark.parametrize('invalid', [None, 0, -1, True, 'bad', float('inf'), float('nan')])
def test_iqr_rejects_invalid_amounts_without_stopping_other_indicators(invalid):
    iqr = iqr_finding(invalid, list(range(1, 40)))
    assert iqr['detected'] is None and iqr['reason'] == 'importe_ausente_o_invalido'
    result = baseline_coverage(values(directas_90d=3), 'ADJUDICACION', iqr)
    assert result['confirmed_signal_count'] == 1 and result['complete_score'] is None


def test_iqr_invalid_peers_are_excluded_and_do_not_satisfy_minimum():
    result = iqr_finding(100, [1, 2, None, True, float('inf'), float('nan'), -1, 'bad'] * 5)
    assert result['n'] == 10 and result['invalid_peers'] == 30
    assert result['detected'] is None and result['reason'] == 'grupo_insuficiente'


def test_prepared_iqr_reference_reuses_thresholds_without_changing_findings():
    peers = list(range(1, 51)) + [None, True, -3, 'invalid']
    reference = iqr_reference(peers)
    for amount in (None, 1, 25, 51, 500):
        assert iqr_finding_from_reference(amount, reference) == iqr_finding(amount, peers)


def row(amount, when='2026-01-01T00:00:00Z', **changes):
    return {'prediction_at': when, 'values': {'log_adjudicado': log1p(amount), 'log_presupuesto': log1p(amount),
                                             'categoria': 'A', **values()}, **changes}


def test_chronological_report_exposes_operation_and_aggregate_coverage():
    history = [row(i) for i in range(1, 32)]
    target = row(1000)
    scores, report = chronological_baseline(history, [target], 'ADJUDICACION')
    assert scores == [1] and report['complete_rows'] == 1
    assert report['operation_coverage'][0]['complete_score'] == 1
    assert report['family_status_counts']['IMPORTE_ATIPICO'] == {'DETECTADA': 1}


def test_equivalent_timezones_are_one_landmark_and_future_peers_do_not_leak():
    history = [row(i, '2026-01-01T00:00:00Z') for i in range(1, 30)]
    target = row(1000, '2025-12-31T19:00:00-05:00')
    future = [row(100000, '2026-01-01T00:00:01Z') for _ in range(100)]
    scores, report = chronological_baseline(history + future, [target], 'ADJUDICACION')
    assert scores == [1] and report['iqr_evaluable_rows'] == 1
    assert report['operation_coverage'][0]['indicators']['IMPORTE_ATIPICO']['observed']['n'] == 30


def test_partial_comparator_does_not_claim_complete_zero():
    target = row(1)
    target['values']['directas_90d'] = None
    scores, report = chronological_baseline([], [target], 'ADJUDICACION')
    assert scores == [0] and report['complete_rows'] == 0
    assert report['score_semantics'] == 'confirmed_signal_count_lower_bound'
    assert report['operation_coverage'][0]['complete_score'] is None


def test_stage_mismatch_and_invalid_stage_are_rejected():
    with pytest.raises(ValueError):
        chronological_baseline([], [row(1, stage='ADJUDICACION')], 'CONVOCATORIA')
    with pytest.raises(ValueError):
        chronological_baseline([], [], 'UNKNOWN')


def test_absent_cohort_fields_cannot_create_an_evaluable_iqr():
    targets = [row(i) for i in range(1, 32)]
    for target in targets:
        target['values']['categoria'] = None
    _, report = chronological_baseline([], targets, 'ADJUDICACION')
    assert report['iqr_evaluable_rows'] == 0
    assert report['operation_coverage'][0]['indicators']['IMPORTE_ATIPICO']['reason'] == 'categoria_o_modalidad_ausente'


def test_offline_cli_preserves_target_order_and_will_not_overwrite(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path
    backend = Path(__file__).resolve().parents[1]
    source, output = tmp_path / 'input.json', tmp_path / 'output.json'
    source.write_text(json.dumps({'stage': 'ADJUDICACION', 'history': [], 'targets': [row(1)]}), encoding='utf-8')
    command = [sys.executable, '-I', str(backend / 'scripts/risk_baseline_coverage.py'),
               '--input', str(source), '--output', str(output)]
    result = subprocess.run(command, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding='utf-8'))
    assert report['coverage']['operation_coverage'][0]['complete_score'] is None
    assert report['scores_lower_bound'] == [0]
    assert not report['database_accessed'] and not report['publication_authorized']
    assert len(report['implementation_sha256']) == 4
    before = output.read_bytes()
    assert subprocess.run(command, capture_output=True, timeout=20).returncode != 0
    assert output.read_bytes() == before
