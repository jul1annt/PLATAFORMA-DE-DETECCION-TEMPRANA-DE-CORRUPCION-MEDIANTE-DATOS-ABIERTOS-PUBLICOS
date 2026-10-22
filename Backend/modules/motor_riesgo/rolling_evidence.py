"""Offline complete-frame rolling evidence; current cuts are never stage history."""
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal, InvalidOperation, localcontext
from .domain import digest, instant, official_id
from .cut_rules import TEMPORAL_SCOPE

POLICY = 'verified-pair-rolling-current-cut-v2'


def monetary_value(value, currency):
    """NUMERIC(38,2) positive amounts, explicit three-letter currency, no rounding.

    Currency syntax does not prove the denomination in the original document.
    The 128-character bound also prevents pathological decimal representations.
    """
    if (isinstance(value, bool) or not isinstance(currency, str) or len(currency) != 3
            or not currency.isascii() or not currency.isupper() or not currency.isalpha()):
        return None, None
    try:
        raw = str(value)
        if len(raw) > 128:
            return None, None
        amount = Decimal(raw)
        if not amount.is_finite() or not 0 < amount < Decimal('1e36'):
            return None, None
        with localcontext() as context:
            context.prec = 64
            cents = amount.quantize(Decimal('0.01'))
        return (cents, currency) if cents == amount else (None, None)
    except (ValueError, InvalidOperation, TypeError):
        return None, None


def assess(payload):
    """Require the entire buyer/supplier pair, all methods/categories, for 90 days.

    Events are award dates, not publication dates. Multiple awards remain traceable
    but frequency counts distinct source/process units. Unknowns cannot prove zero.
    """
    with localcontext() as context:
        # At most 20,000 NUMERIC(38,2) awards; 64 digits retain every cent.
        context.prec = 64
        return _assess(payload)


def _assess(payload):
    scope, target, rows = payload['scope'], payload['target'], payload['rows']
    if scope.get('temporal_scope') != TEMPORAL_SCOPE:
        raise ValueError('Solo se admite evidencia descriptiva del corte actual')
    if (not isinstance(rows, list) or len(rows) > 20000 or type(scope.get('raw_rows')) is not int
            or scope['raw_rows'] != len(rows) or type(scope.get('complete_pair_history')) is not bool):
        raise ValueError('Marco de historia inválido')
    at, start, end = (instant(value) for value in (target['award_at'], scope['start'], scope['end']))
    if not start <= at <= end:
        raise ValueError('Objetivo fuera del marco temporal')
    pair = (official_id(target.get('buyer_key')), official_id(target.get('supplier_key')))
    source, process, award = (target.get('source_id'), official_id(target.get('process_id')), official_id(target.get('award_id')))
    if (None in pair or type(source) is not int or source < 1 or not process or not award
            or target.get('identity_verified') is not True):
        raise ValueError('Objetivo sin identidad comprobada')
    reasons = {'reiteraciones_30d': Counter(), 'directas_90d': Counter()}
    for field, days in (('reiteraciones_30d', 30), ('directas_90d', 90)):
        if not scope['complete_pair_history'] or start > at - timedelta(days=days):
            reasons[field]['historia_incompleta'] += 1
    category = official_id(target.get('category'))
    if not category: reasons['reiteraciones_30d']['categoria_objetivo_ausente'] += 1
    groups = defaultdict(list)
    ignored = Counter()
    for row in rows:
        if (official_id(row.get('buyer_key')), official_id(row.get('supplier_key'))) != pair:
            raise ValueError('Fila ajena al par entidad/proveedor declarado')
        if row.get('source_id') == source and official_id(row.get('process_id')) == process:
            ignored['proceso_objetivo'] += 1
            continue
        try:
            when = instant(row['award_at'])
        except (ValueError, TypeError, KeyError, AttributeError):
            for counter in reasons.values(): counter['fecha_adjudicacion_invalida'] += 1
            continue
        if when > at:
            ignored['evento_futuro'] += 1
            continue
        if when < at - timedelta(days=90):
            ignored['fuera_de_ventana'] += 1
            continue
        key = (row.get('source_id'), official_id(row.get('process_id')), official_id(row.get('award_id')))
        if (type(key[0]) is not int or key[0] < 1 or not key[1] or not key[2]
                or row.get('identity_verified') is not True):
            reasons['directas_90d']['identidad_no_comprobada'] += 1
            if when >= at - timedelta(days=30): reasons['reiteraciones_30d']['identidad_no_comprobada'] += 1
            continue
        groups[key].append((when, row))
    selected = {'reiteraciones_30d': [], 'directas_90d': []}
    for key, copies in sorted(groups.items()):
        # Exact copies are harmless; inconsistent snapshots require reconciliation.
        fingerprints = {digest({field: row.get(field) for field in
                        ('award_at', 'category', 'direct', 'method_semantics_verified', 'amount', 'currency', 'method', 'justification')})
                        for _, row in copies}
        if len(fingerprints) != 1:
            reasons['directas_90d']['versiones_contradictorias'] += 1
            if any(when >= at - timedelta(days=30) for when, _ in copies):
                reasons['reiteraciones_30d']['versiones_contradictorias'] += 1
            continue
        when, row = copies[0]
        evidence = {'source_id': key[0], 'process_id': key[1], 'award_id': key[2],
                    'award_at': when.isoformat(), 'method': row.get('method'),
                    'justification': row.get('justification'), 'amount': row.get('amount'),
                    'currency': row.get('currency')}
        if (type(row.get('direct')) is not bool or row.get('method_semantics_verified') is not True
                or not official_id(row.get('method'))):
            reasons['directas_90d']['modalidad_no_verificada'] += 1
        elif row['direct']:
            selected['directas_90d'].append(evidence)
        if when >= at - timedelta(days=30):
            other_category = official_id(row.get('category'))
            if not other_category:
                reasons['reiteraciones_30d']['categoria_ausente'] += 1
            elif category and other_category == category:
                selected['reiteraciones_30d'].append(evidence)
    indicators = {}
    for field, evidence in selected.items():
        processes = {(row['source_id'], row['process_id']) for row in evidence}
        totals, invalid_amounts = defaultdict(Decimal), 0
        for row in evidence:
            amount, currency = monetary_value(row['amount'], row['currency'])
            if amount is None:
                invalid_amounts += 1
            else:
                totals[currency] += amount
        indicators[field] = {'count': len(processes) if not reasons[field] else None,
                             'observed_distinct_processes': len(processes),
                             'observed_awards': len(evidence), 'reasons': dict(reasons[field]),
                             'amounts_by_currency': {currency: str(value) for currency, value in sorted(totals.items())},
                             'amounts_complete': not reasons[field] and not invalid_amounts,
                             'awards_without_verified_amount_currency': invalid_amounts,
                             'evidence': evidence}
    values = {field: result['count'] for field, result in indicators.items()}
    return {'policy': POLICY, 'temporal_scope': TEMPORAL_SCOPE,
            'monetary_policy': 'positive-numeric38-2-no-rounding-v1',
            'currency_verification': 'input_declared_code_not_documentary',
            'frame': {'start': start.isoformat(), 'end': end.isoformat(),
                      'complete_pair_history': scope['complete_pair_history'],
                      'universe': scope.get('universe', 'declared_input_frame_only'),
                      'snapshot_cut': scope.get('snapshot_cut'),
                      'coverage_outside_declared_universe_verified': False}, 'target':
            {'source_id': source, 'process_id': process, 'award_id': award, 'award_at': at.isoformat()},
            'values': values, 'indicators': indicators, 'ignored': dict(ignored),
            'frame_sha256': digest(payload), 'training_eligible': False, 'publication_authorized': False,
            'limitations': ['Ventanas inclusivas [t-días,t], excluyen todo el proceso objetivo.',
                            'Reiteración no acredita fraccionamiento ni duplicación.',
                            'Contratación directa no acredita una conducta ilícita.',
                            'No mide cuota de mercado: el denominador de la entidad no está incluido.',
                            'Datos actuales no reconstruyen conocimiento histórico.']}
