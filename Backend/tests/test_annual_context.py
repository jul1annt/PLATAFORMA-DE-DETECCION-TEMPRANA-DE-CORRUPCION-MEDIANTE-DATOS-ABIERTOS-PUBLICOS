"""Complete annual denominators cannot be inferred by dropping unknown records."""
from datetime import datetime, timedelta, timezone
import pytest
from modules.motor_riesgo.annual_context import assess

AT='2020-04-01T05:00:00+00:00'


def item(process='P', supplier='S', **changes):
    return {'source_id':1,'process_id':process,'award_id':'A-'+process,'source_row_id':'ROW-'+process,
            'buyer_key':'BUYER','raw_buyer_key':'BUYER','supplier_key':supplier,
            'published_at':'2020-03-01T05:00:00+00:00','awarded_at':'2020-03-20T05:00:00+00:00',
            'awarded':'SI','unit_rows':1,**changes}


def evaluate(rows, **kwargs): return assess(rows,item('TARGET'),AT,**kwargs)


def test_own_process_excluded_before_date_and_identity_checks():
    result=evaluate([item('TARGET',published_at=None,awarded_at=None,unit_rows=2),item('OTHER')])
    assert result['buyer_previous']==result['market_processes']==1
    assert result['concentration']==1 and result['market_bad_rows']==result['publication_bad_rows']==0


@pytest.mark.parametrize('changes', [{'awarded_at':None},{'supplier_key':None},{'award_id':None},
    {'process_id':None},{'unit_rows':2},{'awarded':'UNKNOWN'},{'buyer_key':None},
    {'buyer_key':'OTHER','raw_buyer_key':'BUYER'}])
def test_uncertainty_blocks_market_but_preserves_other_evidence(changes):
    result=evaluate([item('GOOD'),item('BAD',**changes)])
    assert result['concentration'] is None and not result['market_complete']
    assert result['market_bad_rows']==1


def test_publication_unknown_does_not_erase_known_award_date():
    result=evaluate([item(published_at=None)])
    assert result['buyer_previous'] is None and result['publication_bad_rows']==1
    assert result['concentration']==1 and result['market_complete']


def test_old_publication_cannot_hide_award_with_unknown_date():
    result=evaluate([item(published_at='2010-01-01T00:00:00Z',awarded_at=None)])
    assert result['buyer_previous']==0 and result['concentration'] is None


def test_multiple_awards_and_winners_do_not_multiply_denominator():
    result=evaluate([item('P','S',award_id='A1'),item('P','S',award_id='A2'),item('P','T',award_id='A3')])
    assert result['market_processes']==1 and result['max_supplier_processes']==1
    assert result['concentration']==1  # Participation in processes; deliberately not HHI.
    assert 'not_monetary_share_or_hhi' in result['metric']


def test_same_process_text_in_distinct_sources_is_distinct():
    result=evaluate([item('P','S'),item('P','T',source_id=2)])
    assert result['market_processes']==2 and result['concentration']==0.5


def test_empty_and_incomplete_frames_never_publish_a_ratio():
    result=evaluate([])
    assert result['buyer_previous']==0 and result['market_processes']==0 and result['concentration'] is None
    result=evaluate([item()],frame_complete=False)
    assert result['buyer_previous'] is None and result['concentration'] is None


@pytest.mark.parametrize('changes',[{'unit_rows':True},{'raw_buyer_key':'OTHER'},{'source_row_id':None}])
def test_invalid_target_identity_cannot_receive_annual_features(changes):
    with pytest.raises(ValueError):assess([item()],item('TARGET',**changes),AT)


def test_boundaries_are_elapsed_hours_and_ignore_future_publication():
    start=(datetime.fromisoformat(AT)-timedelta(hours=8760)).isoformat()
    old=(datetime.fromisoformat(start)-timedelta(seconds=1)).isoformat()
    result=evaluate([item('AT_START',published_at=start,awarded_at=start),
                     item('OLD',published_at=old,awarded_at=old),
                     item('FUTURE_AWARD',awarded_at='2020-04-02T00:00:00Z'),
                     item('FUTURE_PUB',published_at='2020-04-02T00:00:00Z')])
    assert result['buyer_previous']==2 and result['market_processes']==1 and result['concentration']==1


def test_pruning_preserves_both_denominators_and_unknown_dates():
    import random
    from modules.motor_riesgo.annual_context import eligible_for_frame
    rng=random.Random(20261020);at=datetime.fromisoformat(AT)
    for _ in range(100):
        rows=[item(str(i),supplier='S'+str(rng.randrange(3)),
                   published_at=(at-timedelta(days=rng.randrange(-20,800))).isoformat() if rng.randrange(5) else None,
                   awarded_at=(at-timedelta(days=rng.randrange(-20,800))).isoformat() if rng.randrange(4) else None,
                   awarded=rng.choice(['SI','NO','UNKNOWN'])) for i in range(30)]
        assert evaluate(rows)==evaluate([row for row in rows if eligible_for_frame(row,AT)])
