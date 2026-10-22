"""Explicit baselines. An unevaluable indicator is never a negative finding."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from .domain import REFERENCES
from .baseline_coverage import baseline_coverage, POLICY


def _positive(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() and number > 0 else None


def iqr_reference(peers: list) -> dict:
    """Prepare a peer group once; reuse its thresholds for each target row."""
    usable = sorted(number for x in peers if (number := _positive(x)) is not None)
    result = {"indicator": "IMPORTE_ATIPICO", "reference": REFERENCES["ocp"], "n": len(usable), "detected": None,
              "invalid_peers": len(peers) - len(usable)}
    if len(usable) < 30:
        return {**result, "reason": "grupo_insuficiente"}
    def quantile(p):
        pos = Decimal(len(usable) - 1) * Decimal(str(p))
        lo = int(pos)
        return usable[lo] + (usable[min(lo + 1, len(usable) - 1)] - usable[lo]) * (pos - lo)
    q1, q3 = quantile(.25), quantile(.75)
    spread = q3 - q1
    if spread <= 0:
        return {**result, "reason": "iqr_cero"}
    lower, upper = q1 - Decimal('1.5') * spread, q3 + Decimal('1.5') * spread
    return {**result, "q1": q1, "q3": q3, "lower": lower, "upper": upper}


def iqr_finding_from_reference(value, reference: dict) -> dict:
    result = {key: item for key, item in reference.items() if key not in {"q1", "q3", "lower", "upper"}}
    amount = _positive(value)
    if amount is None:
        return {**result, "reason": "importe_ausente_o_invalido"}
    if reference.get("reason"):
        return {**result, "reason": reference["reason"]}
    q1, q3, lower, upper = (reference[key] for key in ("q1", "q3", "lower", "upper"))
    return {**result, "detected": amount < lower or amount > upper, "value": str(amount),
            "q1": str(q1), "q3": str(q3), "lower": str(lower), "upper": str(upper),
            "explanation": "Importe fuera del rango de sus pares; no acredita sobreprecio."}


def iqr_finding(value, peers: list) -> dict:
    return iqr_finding_from_reference(value, iqr_reference(peers))


def rolling_context(rows: list[dict], current: dict) -> dict:
    """Reference implementation for parity tests; production uses indexed SQL."""
    at = current['at']
    eligible = [x for x in rows if x['at'] <= at and x.get('process_id') and x['process_id'] != current['process_id']
                and current.get('supplier_key') and current.get('buyer_key')
                and x.get('supplier_key') == current['supplier_key'] and x.get('buyer_key') == current['buyer_key']]
    repeated = {x['process_id'] for x in eligible if at - timedelta(days=30) <= x['at'] and x.get('category') == current.get('category')}
    direct = {x['process_id'] for x in eligible if at - timedelta(days=90) <= x['at'] and x.get('direct')}
    return {"reiteraciones_30d": len(repeated), "directas_90d": len(direct)}


def baseline(values: dict) -> float:
    # Compatibility helper: a lower-bound count, never a complete risk score.
    return float(baseline_coverage(values, 'ADJUDICACION')['confirmed_signal_count'])


def chronological_baseline(history: list[dict], targets: list[dict], stage: str) -> tuple[list[float], dict]:
    """IQR reference uses category/method/year and observations available by t.

    Peer entries are deduplicated by official process ID where available. This
    comparator never learns from judicial labels or from later target snapshots.
    """
    from collections import defaultdict
    from math import expm1, isfinite
    from .domain import instant, operation_key
    if stage not in ('CONVOCATORIA', 'ADJUDICACION'):
        raise ValueError('Etapa inválida')
    cohorts = defaultdict(dict)
    by_time = defaultdict(list)
    for row in history + targets:
        if row.get('stage', stage) != stage:
            raise ValueError('El comparador requiere una sola etapa')
        by_time[instant(row['prediction_at'])].append(row)
    evaluated = {}
    details = {}
    eligible_count = 0
    amount = 'log_presupuesto' if stage == 'CONVOCATORIA' else 'log_adjudicado'
    target_ids = {id(r) for r in targets}
    for timestamp in sorted(by_time):
        for row in by_time[timestamp]:
            values = row['values']
            key = (values.get('categoria'), values.get('modalidad'), timestamp.year)
            process = operation_key(row, stage) if row.get('source_id') and row.get('process_id') else ('synthetic_missing_identity', id(row))
            try:
                value = expm1(values[amount]) if values.get(amount) is not None else None
            except (ValueError, TypeError, OverflowError):
                value = None
            if value is not None and isfinite(value) and value > 0:
                cohorts[key][process] = value
        for row in by_time[timestamp]:
            if id(row) not in target_ids:
                continue
            values = row['values']
            key = (values.get('categoria'), values.get('modalidad'), timestamp.year)
            try:
                original_amount = expm1(values[amount]) if values.get(amount) is not None else None
            except (ValueError, TypeError, OverflowError):
                original_amount = None
            peers = list(cohorts[key].values()) if key[0] and key[1] else []
            result = iqr_finding(original_amount, peers)
            if not key[0] or not key[1]:
                result.update(detected=None, reason='categoria_o_modalidad_ausente')
            eligible_count += result['detected'] is not None
            coverage = baseline_coverage(values, stage, result)
            evaluated[id(row)] = float(coverage['confirmed_signal_count'])
            details[id(row)] = coverage
    from collections import Counter
    coverage_rows = [details[id(r)] for r in targets]
    return [evaluated[id(r)] for r in targets], {'iqr_evaluable_rows': eligible_count, 'total_rows': len(targets),
             'policy': POLICY, 'score_semantics': 'confirmed_signal_count_lower_bound',
             'operation_coverage': coverage_rows,
             'family_status_counts': {name: dict(Counter(r['families'][name]['status'] for r in coverage_rows))
                                      for name in ('IMPORTE_ATIPICO', 'COMPETENCIA', 'CONCENTRACION_REITERACION')},
             'indicator_status_counts': {name: dict(Counter(r['indicators'][name]['status'] for r in coverage_rows))
                                         for name in ('IMPORTE_ATIPICO', 'OFERENTE_UNICO', 'DIRECTAS_90D', 'REITERACION_30D')},
             'complete_rows': sum(details[id(r)]['complete_score'] is not None for r in targets),
             'formula': 'conteo de familias de señales aplicables, IQR sin futuro; desconocido no acredita ausencia',
             'period': 'año', 'min_peers': 30}
