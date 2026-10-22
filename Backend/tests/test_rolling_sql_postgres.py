"""Compare independent SQL aggregates with offline count/quality semantics."""
import copy
from datetime import datetime, timedelta, timezone
import random
import pytest
from sqlalchemy import text
from modules.motor_riesgo.rolling_sql_check import compare
from test_rolling_evidence import frame, row


def check(db, rows, data=None):
    payload = copy.deepcopy(data or frame())
    payload['rows'] = rows; payload['scope']['raw_rows'] = len(rows)
    result = compare(db, payload)
    assert result['match'], result
    assert not result['database_writes'] and result['monetary_parity_checked']
    assert not result['legacy_history_parity_checked']
    return result['sql']


def test_positive_signals_multiple_awards_and_sources(postgres_test_session):
    rows = [row('P1'), row('P1', award_id='A2'), row('P1', source_id=2), row('P3')]
    result = check(postgres_test_session, rows)
    assert result['indicators']['directas_90d']['count'] == 3
    assert result['indicators']['reiteraciones_30d']['count'] == 3
    assert result['indicators']['directas_90d']['observed_awards'] == 4


@pytest.mark.parametrize('changes', [
    {'identity_verified': False}, {'source_id': None}, {'source_id': True}, {'source_id': -1},
    {'process_id': 'N/A'}, {'award_id': None}, {'award_at': None}, {'award_at': '2020-03-20'},
    {'direct': None}, {'direct': 1}, {'method_semantics_verified': False}, {'method': None},
    {'category': None}, {'category': 'OTHER'}, {'direct': False}, {'amount': None},
    {'amount': 'NaN'}, {'award_at': '2020-04-02T00:00:00-05:00'},
    {'award_at': '2019-01-01T00:00:00-05:00'},
])
def test_missing_and_invalid_fields(postgres_test_session, changes):
    check(postgres_test_session, [row('OK'), row('OTHER', **changes)])


@pytest.mark.parametrize('changes', [{'amount': '99'}, {'category': 'OTHER'}, {'direct': False},
                                     {'method_semantics_verified': False}])
def test_conflicting_versions(postgres_test_session, changes):
    result = check(postgres_test_session, [row(), row(**changes)])
    assert result['indicators']['directas_90d']['count'] is None


def test_duplicates_target_exclusion_and_missing_category(postgres_test_session):
    data = frame(); data['target']['category'] = None
    result = check(postgres_test_session, [row(), row(), row('TARGET', award_at=None)], data)
    assert result['indicators']['directas_90d']['count'] == 1
    assert result['indicators']['reiteraciones_30d']['count'] is None
    assert result['ignored'] == {'proceso_objetivo': 1}


@pytest.mark.parametrize('complete,start', [(True, '2020-03-01T00:00:00-05:00'),
                                           (False, '2020-01-01T00:00:00-05:00')])
def test_incomplete_history(postgres_test_session, complete, start):
    data = frame(); data['scope'].update(complete_pair_history=complete, start=start)
    check(postgres_test_session, [row()], data)


@pytest.mark.parametrize('tz', ['UTC', 'America/Bogota', 'America/New_York'])
def test_exact_boundaries_do_not_depend_on_database_timezone(postgres_test_session, tz):
    db = postgres_test_session
    db.execute(text('SELECT set_config(:name,:value,true)'), {'name': 'TimeZone', 'value': tz})
    rows = [row('30', award_at='2020-03-02T05:00:00+00:00'),
            row('90', award_at='2020-01-02T05:00:00+00:00'),
            row('OUT30', award_at='2020-03-02T04:59:59+00:00'),
            row('OUT90', award_at='2020-01-02T04:59:59+00:00'),
            row('AT', award_at='2020-04-01T05:00:00+00:00'),
            row('FUTURE', award_at='2020-04-01T05:00:01+00:00')]
    result = check(db, rows)
    assert result['indicators']['directas_90d']['count'] == 4
    assert result['indicators']['reiteraciones_30d']['count'] == 2


def test_empty_complete_frame(postgres_test_session):
    result = check(postgres_test_session, [])
    assert result['indicators']['directas_90d']['count'] == 0


def test_money_sums_preserve_cents_and_currencies(postgres_test_session):
    rows = [row('LARGE', amount='123456789012345678901234567890123456.78'),
            row('CENT', amount='0.01'), row('USD', amount='1.23', currency='USD'),
            row('USD', amount='1.23', currency='USD')]
    result = check(postgres_test_session, rows)['indicators']['directas_90d']
    assert result['amounts_by_currency'] == {'COP': '123456789012345678901234567890123456.79', 'USD': '1.23'}
    assert result['amounts_complete'] and result['observed_awards'] == 3


@pytest.mark.parametrize('changes', [{'amount': '0.001'}, {'amount': '1e36'}, {'amount': None},
                                     {'currency': None}, {'currency': 'cop'}, {'amount': True}])
def test_invalid_money_keeps_frequency_but_abstains_on_total(postgres_test_session, changes):
    result = check(postgres_test_session, [row('VALID'), row('BAD', **changes)])['indicators']['directas_90d']
    assert result['count'] == 2 and result['amounts_by_currency'] == {'COP': '10.00'}
    assert not result['amounts_complete'] and result['awards_without_verified_amount_currency'] == 1


def test_seeded_mixed_frames(postgres_test_session):
    rng = random.Random(20261019)
    at = datetime(2020, 4, 1, 5, tzinfo=timezone.utc)
    changes = [{}, {'identity_verified': False}, {'direct': None}, {'category': None},
               {'award_at': None}, {'award_id': None}, {'category': 'OTHER'}, {'source_id': 2},
               {'method_semantics_verified': False}, {'direct': False}, {'amount': None}]
    for _ in range(100):
        rows = []
        for i in range(rng.randrange(25)):
            rows.append(row(str(rng.randrange(8)),
                            **({'award_id': str(rng.randrange(3)), 'award_at': (at-timedelta(days=rng.randrange(-10, 110))).isoformat()} |
                               rng.choice(changes))))
        check(postgres_test_session, rows)
