"""Descriptive lab checks; stability is not predictive validation."""
import copy
from decimal import Decimal
import pytest
from modules.motor_riesgo.weight_lab import (FIELDS, assess, digest, empirical_transform, freeze_reference,
                                            overlap, reference_columns, spearman, top_weights)


def sample():
    return {'scope': {'census': True, 'expected_rows': 4},
            'configured_weights': {'OUTLIER': 1, 'DUPLICADO_CORTO': 1.5, 'ABUSO_DIRECTO': 2},
            'rows': [{'id': str(i), 'max_score_outlier': x, 'max_score_duplicado': y, 'score_directo': z}
                     for i, (x, y, z) in enumerate([(0, 0, 0), (10000000000, 0, 0), (1, 10, 0), (2, 0, 10)])]}


def test_complete_census_is_compared_without_changing_input():
    payload = sample()
    before = copy.deepcopy(payload)
    report, reference = assess(payload)
    assert payload == before
    assert report['rows'] == 4 and len(report['variants']) == 5
    assert reference['n'] == 4 and reference['sha256'] == digest({k: v for k, v in reference.items() if k != 'sha256'})
    assert not report['publication_authorized'] and not report['training_performed']
    assert report['variants']['LEGADO']['component_contribution_share']['OUTLIER'] > .999
    assert max(report['variants']['ACOTADO_PESOS_IGUALES']['component_contribution_share'].values()) < .6


def test_ties_have_fractional_mass_and_permutation_does_not_change_comparison():
    scores = [Decimal(1)] * 100
    weights = top_weights(scores, Decimal('.05'))
    assert all(x == Decimal('.05') for x in weights)
    assert sum(weights) == 5 and overlap(scores, scores, Decimal('.05')) == 1
    a, b = [4, 3, 2, 1], [1, 2, 3, 4]
    assert overlap(a, b, Decimal('.25')) == 0
    assert overlap(a[::-1], b[::-1], Decimal('.25')) == 0


def test_frozen_reference_does_not_refit_to_new_observations():
    columns = {key: list(map(Decimal, ('0', '0', '1', '3'))) for key in FIELDS}
    reference = freeze_reference(columns, {'cut': 'old'})
    new = {key: [Decimal(0), Decimal(1), Decimal(2), Decimal(100)] for key in FIELDS}
    changed = empirical_transform(new, reference)
    assert changed['OUTLIER'] == [Decimal(0), Decimal('.625'), Decimal('.75'), Decimal(1)]
    assert reference['n'] == 4


@pytest.mark.parametrize('tamper', ['hash', 'order', 'size', 'policy', 'nan'])
def test_corrupted_or_rehashed_invalid_reference_is_rejected(tamper):
    reference = freeze_reference({key: [Decimal(0), Decimal(1)] for key in FIELDS}, {})
    if tamper == 'hash':reference['sha256'] = 'a' * 64
    else:
        if tamper == 'order':reference['components']['OUTLIER'].reverse()
        elif tamper == 'size':reference['n'] = 3
        elif tamper == 'policy':reference['policy'] = 'unknown'
        else:reference['components']['OUTLIER'][0] = 'NaN'
        reference['sha256'] = digest({k: v for k, v in reference.items() if k != 'sha256'})
    with pytest.raises(ValueError):reference_columns(reference)


@pytest.mark.parametrize('invalid', [None, True, -1, 'NaN', 'Infinity', 'bad'])
def test_unknown_or_invalid_components_are_not_coerced_to_zero(invalid):
    payload = sample(); payload['rows'][0]['max_score_outlier'] = invalid
    with pytest.raises(ValueError):assess(payload)


@pytest.mark.parametrize('tamper', ['count', 'census', 'duplicate', 'missing_id', 'range', 'bool_count'])
def test_incomplete_or_ambiguous_frames_are_rejected(tamper):
    payload = sample()
    if tamper == 'count':payload['scope']['expected_rows'] = 5
    elif tamper == 'census':payload['scope']['census'] = False
    elif tamper == 'duplicate':payload['rows'][0]['id'] = payload['rows'][1]['id']
    elif tamper == 'missing_id':payload['rows'][0].pop('id')
    elif tamper == 'range':payload['rows'][0]['score_directo'] = 11
    else:payload['scope']['expected_rows'] = True
    with pytest.raises(ValueError):assess(payload)


def test_constant_component_has_no_defined_rank_correlation():
    assert spearman([1, 1, 1], [1, 2, 3]) is None
    assert spearman([1, 2, 3], [3, 2, 1]) == -1
    assert spearman([1, 2, 3], [1, 2, 3]) == 1


def test_all_zero_frame_is_not_a_claim_of_discrimination():
    payload = sample()
    for row in payload['rows']:
        row.update({field: 0 for field in FIELDS.values()})
    report, _ = assess(payload)
    for variant in report['variants'].values():
        assert variant['score_summary']['distinct_scores'] == 1
        assert variant['spearman_with_legacy'] is None
        assert all(x is None for x in variant['component_contribution_share'].values())


def test_invalid_ranking_shapes_and_fraction_are_rejected():
    for fraction in (0, -1, True, 2):
        with pytest.raises(ValueError):top_weights([1, 2], fraction)
    with pytest.raises(ValueError):overlap([1], [1, 2], Decimal('.05'))


def test_calculation_does_not_depend_on_ambient_decimal_precision():
    from decimal import localcontext
    expected = assess(sample())
    with localcontext() as context:
        context.prec = 7
        assert assess(sample()) == expected


def test_offline_cli_preserves_artifacts_and_has_bounded_input_contract(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path
    backend = Path(__file__).resolve().parents[1]
    source, output, reference = (tmp_path / name for name in ('input.json', 'report.json', 'reference.json'))
    source.write_text(json.dumps(sample()), encoding='utf-8')
    command = [sys.executable, '-I', str(backend / 'scripts/risk_normalization_lab.py'),
               '--input', str(source), '--output', str(output), '--reference', str(reference)]
    result = subprocess.run(command, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding='utf-8'))
    frozen = json.loads(reference.read_text(encoding='utf-8'))
    assert report['reference_sha256'] == frozen['sha256']
    assert len(report['implementation_sha256']) == 2
    assert not report['database_accessed'] and not report['publication_authorized']
    before = output.read_bytes(), reference.read_bytes()
    assert subprocess.run(command, capture_output=True, timeout=20).returncode != 0
    assert before == (output.read_bytes(), reference.read_bytes())
