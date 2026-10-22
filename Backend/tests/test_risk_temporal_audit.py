"""Chronological exclusions remain auditable and do not relax label timing."""
from copy import deepcopy
import pytest
from analytics_ml.evaluation import temporal_split, validate_split_audit


def synthetic_rows():
    rows = []
    for i in range(30):
        at = f'{2000+i}-01-01T00:00:00+00:00'
        rows.extend([{'prediction_at': at, 'positive': True, 'case_group': str(i),
                      'label_available_at': f'{2000+i}-02-01T00:00:00+00:00'},
                     {'prediction_at': at, 'positive': False, 'case_group': None}])
    # Validation group 20 also has an earlier operation: its boundary excludes
    # the positive row of training group 17. Enough independent cases remain.
    rows.append({**rows[40], 'prediction_at': '2017-01-01T00:00:00+00:00'})
    rows[0]['label_available_at'] = '2099-01-01T00:00:00+00:00'
    rows[36]['label_available_at'] = '2099-01-01T00:00:00+00:00'
    return rows


def test_temporal_audit_accounts_for_exclusions_and_unknown_at_time_labels():
    rows = synthetic_rows()
    original = deepcopy(rows)
    blocks, audit = temporal_split(rows, with_audit=True)
    assert blocks == temporal_split(rows)
    assert rows == original
    assert audit['input_rows'] == 61
    assert audit['excluded_rows'] == 1
    assert sum(audit['split_sizes']) == 60
    assert audit['demoted_future_labels'] == [1, 1, 0]
    validate_split_audit(audit, [len(b) for b in blocks], len(rows))
    groups = [{r['case_group'] for r in b if r['positive']} for b in blocks]
    assert all(len(g) >= 5 for g in groups)
    assert not (groups[0] & groups[1] or groups[1] & groups[2] or groups[0] & groups[2])


@pytest.mark.parametrize('change', ['missing', 'negative', 'boolean', 'sizes', 'reason', 'demoted', 'boundaries', 'cutoffs'])
def test_temporal_audit_rejects_inconsistent_counts_and_boundaries(change):
    rows = synthetic_rows()
    _, audit = temporal_split(rows, with_audit=True)
    sizes = list(audit['split_sizes'])
    if change == 'missing': audit = None
    elif change == 'negative': audit['excluded_rows'] = -1
    elif change == 'boolean': audit['excluded_rows'] = True
    elif change == 'sizes': audit['split_sizes'] = [1, 1, 1]
    elif change == 'reason': audit['exclusions'] = {'unexplained': 1}
    elif change == 'demoted': audit['demoted_future_labels'] = [0, 0, 1]
    elif change == 'boundaries': audit['boundaries']['test_from'] = '1900-01-01T00:00:00Z'
    elif change == 'cutoffs': audit['label_cutoffs'][0] = '2099-01-01T00:00:00Z'
    with pytest.raises(ValueError):
        validate_split_audit(audit, sizes, len(rows))
