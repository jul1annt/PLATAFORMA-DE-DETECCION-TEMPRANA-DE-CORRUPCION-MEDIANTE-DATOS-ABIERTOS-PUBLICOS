"""Reference for prior buyer process participation, not monetary share or HHI."""
from collections import defaultdict
from datetime import timedelta
from .domain import instant, official_id

POLICY = 'buyer-annual-process-participation-v1'


def buyer_key(value):
    key = official_id(value)
    return key if key not in {'0', '-'} else None


def timestamp(value):
    try: return instant(value)
    except (TypeError, ValueError, AttributeError): return None


def eligible_for_frame(row, at):
    """Exact pruning rule; keep unknown dates that can affect either denominator."""
    at=instant(at);start=at-timedelta(hours=8760)
    pub,award=timestamp(row.get('published_at')),timestamp(row.get('awarded_at'))
    potential_award=str(row.get('awarded') or '').strip().upper() not in {'NO','FALSE','0'}
    return ((pub is None or pub<=at) and (pub is None or pub>=start or
            potential_award and (award is None or start<=award<=at)))


def assess(rows, target, at, *, frame_complete=True):
    if type(frame_complete) is not bool or not isinstance(rows, list) or len(rows) > 20000:
        raise ValueError('Marco anual inválido')
    at = instant(at); start = at - timedelta(hours=8760)
    buyer = buyer_key(target.get('buyer_key'))
    process = official_id(target.get('process_id'))
    source = target.get('source_id')
    if (not buyer or not process or type(source) is not int or source < 1
            or not official_id(target.get('source_row_id')) or type(target.get('unit_rows')) is not int or target['unit_rows'] != 1
            or buyer_key(target.get('raw_buyer_key')) not in (None,buyer)):
        raise ValueError('Objetivo anual sin identidad admisible')
    publications, market, suppliers = set(), set(), defaultdict(set)
    bad_pub = bad_market = 0
    for row in rows:
        normalized, raw = buyer_key(row.get('buyer_key')), buyer_key(row.get('raw_buyer_key'))
        if buyer not in (normalized, raw): continue
        normalized_ok = normalized == buyer and (raw is None or raw == buyer)
        key = (row.get('source_id'), official_id(row.get('process_id')))
        if key == (source, process): continue
        pub = timestamp(row.get('published_at'))
        if pub is not None and pub > at: continue
        process_ok = (type(key[0]) is int and key[0] > 0 and key[1]
                      and official_id(row.get('source_row_id')) and normalized_ok)
        if pub is None or start <= pub <= at and not process_ok: bad_pub += 1
        if pub is not None and start <= pub <= at and key[1]: publications.add(key)
        status = str(row.get('awarded') or '').strip().upper()
        if status in {'NO', 'FALSE', '0'}: continue
        awarded = timestamp(row.get('awarded_at'))
        if awarded is not None and not start <= awarded <= at: continue
        supplier = buyer_key(row.get('supplier_key'))
        valid = (process_ok and type(row.get('unit_rows')) is int and row['unit_rows'] == 1
                 and official_id(row.get('award_id')) and supplier and status in {'SI', 'SÍ', 'TRUE', '1'})
        if awarded is None or not valid: bad_market += 1
        if awarded is not None and key[1]: market.add(key)
        if awarded is not None and valid: suppliers[supplier].add(key)
    maximum = max((len(keys) for keys in suppliers.values()), default=0)
    complete = frame_complete and bad_market == 0 and bool(market)
    return {'policy': POLICY, 'buyer_previous': len(publications) if frame_complete and not bad_pub else None,
            'publication_processes': len(publications), 'publication_bad_rows': bad_pub,
            'market_processes': len(market), 'market_bad_rows': bad_market,
            'max_supplier_processes': maximum, 'market_complete': complete,
            'concentration': maximum / len(market) if complete else None,
            'metric': 'maximum_supplier_process_participation_not_monetary_share_or_hhi',
            'target_process_excluded': True, 'outside_universe_coverage_verified': False,
            'training_eligible': False, 'publication_authorized': False}
