"""PU ranking diagnostics, preserving ties and independent judicial case groups."""
from __future__ import annotations
import math
import random
from collections import defaultdict

SPLIT_POLICY = 'chronological-grouped-label-availability-v1'


def hit_weights(scores: list[float], fraction: float) -> list[float]:
    if not scores:
        return []
    if not 0 < fraction <= 1 or not all(math.isfinite(s) for s in scores):
        raise ValueError('Fracción o puntuaciones inválidas')
    # Exact expected review budget: rounding up one operation can materially
    # exceed 5% in small samples. Fractional boundary/tie weights avoid that.
    budget = len(scores) * fraction
    threshold = sorted(scores, reverse=True)[math.ceil(budget) - 1]
    above = sum(s > threshold for s in scores)
    ties = sum(s == threshold for s in scores)
    return [1.0 if s > threshold else (budget - above) / ties if s == threshold else 0.0 for s in scores]


def ranking(rows: list[dict], scores: list[float]) -> dict:
    if len(rows) != len(scores):
        raise ValueError('Cada operación necesita una puntuación')
    positives = [i for i, row in enumerate(rows) if row.get('positive')]
    result = {'rows': len(rows), 'known_positives': len(positives), 'metrics': {}, 'limits': 'Recuperación de positivos conocidos; los no etiquetados no son negativos.'}
    for fraction in (.01, .05, .10):
        weights = hit_weights(scores, fraction)
        recall = sum(weights[i] for i in positives) / len(positives) if positives else None
        result['metrics'][str(fraction)] = {'known_positive_recall': recall, 'lift': recall / fraction if recall is not None else None,
            'expected_reviewed_operations': len(rows) * fraction, 'reviewed_fraction': fraction if rows else None}
    result['boundary_policy'] = 'pesos fraccionales en frontera y empates; presupuesto esperado exacto'
    return result


def paired_case_interval(rows: list[dict], model: list[float], baseline: list[float], *, seed=20261015, repetitions=2000) -> dict:
    model_hits, base_hits = hit_weights(model, .05), hit_weights(baseline, .05)
    groups = defaultdict(list)
    for index, row in enumerate(rows):
        if row.get('positive'):
            groups[row['case_group']].append(model_hits[index] - base_hits[index])
    if len(groups) < 5:
        return {'passed': False, 'reason': 'menos_de_cinco_expedientes_independientes', 'cases': len(groups), 'lower95': None}
    # Equal case weights prevent one large scandal dominating the gate.
    effects = [sum(values) / len(values) for values in groups.values()]
    rng = random.Random(seed)
    boot = sorted(sum(rng.choices(effects, k=len(effects))) / len(effects) for _ in range(repetitions))
    low, high = boot[int(.025 * repetitions)], boot[min(int(.975 * repetitions), repetitions - 1)]
    return {'passed': low > 0, 'cases': len(groups), 'difference': sum(effects) / len(effects), 'lower95': low, 'upper95': high,
            'method': 'paired_case_bootstrap_fixed_top5_tie_aware', 'seed': seed, 'repetitions': repetitions}


def temporal_split(rows: list[dict], *, with_audit=False) -> tuple:
    groups = defaultdict(list)
    for row in rows:
        if row.get('positive'):
            groups[row['case_group']].append(row)
    ordered = sorted(groups, key=lambda g: (max(r['prediction_at'] for r in groups[g]), g))
    if len(ordered) < 15:
        raise ValueError('Se requieren al menos 15 expedientes independientes y cinco por bloque')
    # 60/20/20 where possible, maintaining the approved minimum per block.
    n_test = max(5, len(ordered) // 5)
    n_validation = max(5, len(ordered) // 5)
    sets = (set(ordered[:-n_test-n_validation]), set(ordered[-n_test-n_validation:-n_test]), set(ordered[-n_test:]))
    # Strict interval boundaries: related cases spanning boundaries are excluded.
    boundary1 = min(r['prediction_at'] for g in sets[1] for r in groups[g])
    boundary2 = min(r['prediction_at'] for g in sets[2] for r in groups[g])
    output = ([], [], [])
    excluded_rows = 0
    for row in rows:
        timestamp = row['prediction_at']
        index = 0 if timestamp < boundary1 else 1 if timestamp < boundary2 else 2
        if row.get('positive') and row['case_group'] not in sets[index]:
            excluded_rows += 1
            continue
        output[index].append(row)
    # Unknown-at-the-time positives remain unlabelled. Removing them using a
    # later judicial decision would itself leak the future outcome. Validation
    # labels used to select C must be available before the final-test boundary.
    demoted = [0, 0, 0]
    for index, cutoff in ((0, boundary1), (1, boundary2)):
        demoted[index] = sum(bool(r.get('positive')) and r['label_available_at'] > cutoff for r in output[index])
        output[index][:] = [({**r, 'positive': False, 'case_group': None, 'case_conduct': None,
                             'label_available_at': None} if r.get('positive') and r['label_available_at'] > cutoff else r)
                           for r in output[index]]
    for block in output:
        if len({r['case_group'] for r in block if r.get('positive')}) < 5:
            raise ValueError('Cobertura temporal insuficiente: faltan cinco expedientes por bloque tras evitar fugas')
        if not any(not r.get('positive') for r in block):
            raise ValueError('Falta población sin etiqueta en un bloque temporal')
    if not with_audit:
        return output
    audit = {'policy': SPLIT_POLICY, 'input_rows': len(rows),
             'split_sizes': [len(block) for block in output],
             'excluded_rows': excluded_rows,
             'exclusions': {'case_group_outside_assigned_chronological_block': excluded_rows},
             'demoted_future_labels': demoted,
             'boundaries': {'validation_from': boundary1, 'test_from': boundary2},
             'label_cutoffs': [boundary1, boundary2, None]}
    return output, audit


def validate_split_audit(audit: dict, sizes: list, verified_rows: int) -> None:
    """Account for excluded rows without relaxing chronological eligibility."""
    from modules.motor_riesgo.domain import instant
    if (not isinstance(audit, dict) or audit.get('policy') != SPLIT_POLICY
            or not isinstance(sizes, list) or len(sizes) != 3
            or any(type(n) is not int or n < 1 for n in sizes)
            or type(verified_rows) is not int or verified_rows < 1
            or type(audit.get('input_rows')) is not int or audit['input_rows'] != verified_rows
            or not isinstance(audit.get('split_sizes'), list)
            or any(type(n) is not int for n in audit['split_sizes'])
            or audit.get('split_sizes') != sizes
            or type(audit.get('excluded_rows')) is not int or audit['excluded_rows'] < 0
            or sum(sizes) + audit['excluded_rows'] != verified_rows
            or not isinstance(audit.get('exclusions'), dict)
            or any(type(n) is not int for n in audit['exclusions'].values())
            or audit.get('exclusions') != {'case_group_outside_assigned_chronological_block': audit['excluded_rows']}):
        raise ValueError('Contabilidad de la partición temporal inválida')
    demoted = audit.get('demoted_future_labels')
    if (not isinstance(demoted, list) or len(demoted) != 3
            or any(type(n) is not int or n < 0 or n > size for n, size in zip(demoted, sizes))
            or demoted[2] != 0):
        raise ValueError('Reclasificación temporal de etiquetas inválida')
    boundaries = audit.get('boundaries')
    try:
        if (not isinstance(boundaries, dict)
                or instant(boundaries['validation_from']) >= instant(boundaries['test_from'])
                or audit.get('label_cutoffs') != [boundaries['validation_from'], boundaries['test_from'], None]):
            raise ValueError('Fronteras temporales inválidas')
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Fronteras temporales inválidas') from exc
