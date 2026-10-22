"""Exploratory grouping must not manufacture independent contracts or labels."""
import copy
import pytest
from modules.motor_riesgo.contract_strata import assess, dimensions


def row(i, **changes):
    return {'result_id': str(i), 'source_id': 1, 'source_row_id': f'R{i}', 'process_id': f'P{i}',
            'award_id': f'A{i}', 'awarded': 'Si', 'unit_rows_up_to_two': 1, 'publication_date': '2020-01-01',
            'method': 'Licitación pública', 'category': 'V1.80101500', 'iqr_score': str(i), 'iqr_detected': i > 0,
            'legacy_pair_count': 1, 'valid_pair_count': 1, 'verified_reiteration_score': '2', **changes}


def payload(rows):
    return {'scope': {'unit': 'resultado_contrato_legado', 'selected_rows': len(rows), 'enrichment_completed': True}, 'rows': rows}


def test_grouping_preserves_unit_counts_and_defines_unspsc_as_procurement_segment():
    rows = [row(i) for i in range(40)] + [row(i, publication_date='2021-05-01', method='Contratación directa',
                                           category='43211500') for i in range(40, 80)]
    data = payload(rows); before = copy.deepcopy(data)
    report = assess(data)
    assert data == before and report['eligible_award_units'] == 80
    for dimension in report['strata'].values():
        assert sum(s['rows'] for s in dimension.values()) == 80
    assert set(report['strata']['unspsc_segment']) == {'80', '43'}
    assert report['strata']['publication_year']['2020']['comparison'] is not None
    assert not report['publication_authorized'] and not report['training_performed']


def test_unknown_reiteration_does_not_turn_into_zero():
    report = assess(payload([row(0, legacy_pair_count=0, valid_pair_count=0, verified_reiteration_score=None)]))
    assert report['overall']['reiteration_unknown'] == 1
    assert report['overall']['joint_comparable_rows'] == 0
    assert report['overall']['comparison'] is None


@pytest.mark.parametrize('change,reason', [({'unit_rows_up_to_two': 2}, 'unidad_ambigua_o_sin_comprobacion_global'),
                                         ({'source_row_id': None}, 'identidad_secop_incompleta'),
                                         ({'process_id': 'NO DEFINIDO'}, 'identidad_secop_incompleta'),
                                         ({'award_id': None}, 'sin_adjudicacion_identificable'),
                                         ({'source_id': True}, 'fuente_ausente_o_invalida'),
                                         ({'awarded': 'No'}, 'sin_adjudicacion_identificable')])
def test_invalid_identity_is_excluded_without_inference(change, reason):
    report = assess(payload([row(1, **change)]))
    assert report['eligible_award_units'] == 0 and report['exclusions'][reason] == 1


def test_shared_unit_excludes_all_rows_but_distinct_awards_remain_separate():
    first = row(1); alias = row(2, process_id='P1', award_id='A1')
    report = assess(payload([first, alias]))
    assert report['exclusions']['unidad_repetida_en_seleccion'] == 2
    alias['award_id'] = 'OTHER'
    assert assess(payload([first, alias]))['eligible_award_units'] == 2
    alias['award_id'] = 'A1'; alias['source_id'] = 2
    assert assess(payload([first, alias]))['eligible_award_units'] == 2


def test_incomplete_enrichment_cannot_create_comparable_units():
    data = payload([row(1)]); data['scope']['enrichment_completed'] = False
    assert assess(data)['exclusions']['comprobaciones_globales_pendientes'] == 1


@pytest.mark.parametrize('change', [{'iqr_score': None}, {'iqr_score': 'NaN'}, {'iqr_detected': None},
                                   {'iqr_detected': False, 'iqr_score': 1}])
def test_invalid_iqr_does_not_hide_available_reiteration(change):
    report = assess(payload([row(1, **change)]))
    assert report['overall']['iqr_evaluable'] == 0
    assert report['overall']['reiteration_observed_with_verified_link'] == 1


def test_small_groups_abstain_and_missing_dimensions_are_preserved():
    report = assess(payload([row(1, publication_date=None, method=None, category='bad')]))
    assert report['strata']['publication_year']['SIN_FECHA']['comparison'] is None
    assert 'SIN_UNSPSC_VERIFICABLE' in report['strata']['unspsc_segment']
    assert dimensions(row(1, category='00000000'))['unspsc_segment'] == 'SIN_UNSPSC_VERIFICABLE'


def test_supplier_scores_and_duplicate_result_ids_are_rejected():
    with pytest.raises(ValueError):assess(payload([row(1, score_final=3)]))
    with pytest.raises(ValueError):assess(payload([row(1), row(1)]))


def test_only_complete_rows_enter_ranking_and_each_dimension_preserves_coverage():
    rows = [row(i) for i in range(31)] + [row(i, valid_pair_count=0, verified_reiteration_score=None) for i in range(31, 40)]
    report = assess(payload(rows))
    assert report['overall']['joint_comparable_rows'] == 31
    assert report['overall']['reiteration_unknown'] == 9
    assert report['overall']['comparison'] is not None
    assert report['strata']['publication_year']['2020']['joint_comparable_rows'] == 31


def test_offline_cli_hashes_input_and_preserves_existing_output(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path
    backend = Path(__file__).resolve().parents[1]
    source, output = tmp_path / 'input.json', tmp_path / 'output.json'
    source.write_text(json.dumps(payload([row(1)])), encoding='utf-8')
    command = [sys.executable, '-I', str(backend / 'scripts/risk_contract_strata.py'),
               '--input', str(source), '--output', str(output)]
    result = subprocess.run(command, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding='utf-8'))
    assert report['eligible_award_units'] == 1
    assert len(report['implementation_sha256']) == 4
    assert not report['publication_authorized'] and not report['database_accessed']
    before = output.read_bytes()
    assert subprocess.run(command, capture_output=True, timeout=20).returncode != 0
    assert output.read_bytes() == before
