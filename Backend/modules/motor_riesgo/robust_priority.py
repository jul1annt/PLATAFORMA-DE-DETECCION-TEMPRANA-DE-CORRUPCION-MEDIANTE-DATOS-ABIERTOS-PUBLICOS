"""Descriptive priority bounds under missing evidence and uncertain weights.

No fitting, DB, model inference, publication or corruption probability. Pairwise
linear differences attain their extrema at box vertices. Pattern aggregation
keeps the comparison bounded by family states rather than by contracts squared.
"""
from collections import Counter, defaultdict
from datetime import date
from itertools import product
from .baseline_coverage import (
    POLICY as COVERAGE_POLICY, DETECTED, CLEAR, UNKNOWN, NOT_APPLICABLE, summarize,
)
from .domain import digest

POLICY = 'coverage-and-weight-robust-priority-v1'
FAMILIES = ('IMPORTE_ATIPICO', 'COMPETENCIA', 'CONCENTRACION_REITERACION')
STATES = {DETECTED, CLEAR, UNKNOWN, NOT_APPLICABLE}
MAX_TARGETS = 100_000
WEIGHT_TICKS = (80, 120)


def methodology():
    return {
        'policy': POLICY, 'coverage_policy': COVERAGE_POLICY,
        'central_family_weights': dict.fromkeys(FAMILIES, 1),
        'weight_range': {'minimum': '0.80', 'maximum': '1.20'},
        'weight_range_is_calibrated': False,
        'weight_range_basis': 'Engineering sensitivity around equal weights; not an estimated confidence interval.',
        'missing_family_contribution': '[0, weight]',
        'comparison_group': 'same declared cohort, stage and applicable families',
        'rank_bounds': 'Conservative bounds for all missing-family completions and every shared weight vector inside the box; ties may occupy any position.',
        'ranking_is_total_order': False, 'index_0_100': False,
        'corruption_probability': False, 'publication_authorized': False,
        'family_or_limit': 'A confirmed family need not mean all its indicators were observed.',
    }


def _pattern(coverage):
    if not isinstance(coverage, dict) or coverage.get('policy') != COVERAGE_POLICY:
        raise ValueError('Política de cobertura incompatible')
    stage = coverage.get('stage')
    if stage not in ('CONVOCATORIA', 'ADJUDICACION'):
        raise ValueError('Etapa inválida')
    indicators = coverage.get('indicators')
    required = {'IMPORTE_ATIPICO','OFERENTE_UNICO','DIRECTAS_90D','REITERACION_30D'}
    if not isinstance(indicators, dict) or set(indicators) != required:
        raise ValueError('Indicadores incompletos')
    for name, finding in indicators.items():
        if (not isinstance(finding, dict) or finding.get('indicator') != name
                or finding.get('status') not in STATES):
            raise ValueError('Estado de indicador inválido')
        expected = True if finding['status'] == DETECTED else False if finding['status'] == CLEAR else None
        if finding.get('detected') is not expected:
            raise ValueError('Estado y detección incompatibles')
        if name == 'IMPORTE_ATIPICO' and finding['status'] == NOT_APPLICABLE:
            raise ValueError('Importe debe conservar evaluación o abstención')
        if stage == 'CONVOCATORIA' and name != 'IMPORTE_ATIPICO' and finding['status'] != NOT_APPLICABLE:
            raise ValueError('Señal de adjudicación en convocatoria')
        if stage == 'ADJUDICACION' and name in ('DIRECTAS_90D','REITERACION_30D') and finding['status'] == NOT_APPLICABLE:
            raise ValueError('Ventana de adjudicación debe conservar abstención')
    expected = summarize(stage, indicators)
    for key in ('families','confirmed_signal_count','applicable_families','evaluated_families',
                'unevaluable_families','complete_score','score_interval',
                'evaluated_indicators','applicable_indicators'):
        if coverage.get(key) != expected[key]:
            raise ValueError('Cobertura o pesos no coinciden con evidencia')
    return stage, tuple(expected['families'][name]['status'] for name in FAMILIES)


def _bounds(pattern, weights):
    return (sum(w for s,w in zip(pattern,weights) if s == DETECTED),
            sum(w for s,w in zip(pattern,weights) if s in (DETECTED,UNKNOWN)))


def assess(report):
    """Consume the corrected joint baseline; do not reinterpret legacy scores."""
    if (not isinstance(report, dict) or report.get('policy') != 'current-cut-joint-families-v1'
            or report.get('temporal_scope') != 'current_cut_descriptive_not_stage_prediction'
            or report.get('training_eligible') is not False
            or report.get('publication_authorized') is not False):
        raise ValueError('Se requiere composición descriptiva no publicada')
    rows = report.get('results')
    cut = report.get('snapshot_cut')
    if not isinstance(cut,str):
        raise ValueError('Corte ausente')
    try:
        if date.fromisoformat(cut).isoformat() != cut:
            raise ValueError('Corte no canónico')
    except ValueError as exc:
        raise ValueError('Corte inválido') from exc
    if (not isinstance(rows,list) or not 0 < len(rows) <= MAX_TARGETS
            or type(report.get('targets')) is not int or report['targets'] != len(rows)):
        raise ValueError('Cantidad de objetivos inválida')
    reference = report.get('cohort_canonical_sha256')
    if (not isinstance(reference,str) or len(reference) != 64
            or any(c not in '0123456789abcdef' for c in reference)):
        raise ValueError('Referencia de cohorte ausente')
    groups, items, seen = defaultdict(Counter), [], set()
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError('Objetivo inválido')
        key = row.get('contract_id')
        if type(key) is not int or key < 1 or key in seen:
            raise ValueError('Identidad local inválida o repetida')
        seen.add(key)
        if (row.get('snapshot_cut') != report.get('snapshot_cut')
                or row.get('publication_authorized') is not False
                or row.get('training_eligible') is not False):
            raise ValueError('Corte o uso incompatible')
        stage, pattern = _pattern(row.get('coverage'))
        # Scope/application changes never create cross-stage or cross-scope ranks.
        applicable = tuple(s != NOT_APPLICABLE for s in pattern)
        group = (stage, applicable)
        groups[group][pattern] += 1
        items.append((key,group,pattern,row['coverage']))

    summaries, per_pattern = [], {}
    for group, counts in sorted(groups.items()):
        stage, applicable = group
        n = sum(counts.values())
        vertices = tuple(product(*(WEIGHT_TICKS if a else (0,) for a in applicable)))
        bounds = {p:tuple(_bounds(p,w) for w in vertices) for p in counts}
        group_id = digest({'cohort':reference,'stage':stage,'applicable':applicable})
        # With three families there are at most 27 patterns per application group.
        for pattern in counts:
            guaranteed_before = possible_before = 0
            for other, quantity in counts.items():
                differences = tuple((b[0]-a[1], b[1]-a[0])
                                    for a,b in zip(bounds[pattern],bounds[other]))
                if min(v[0] for v in differences) > 0:
                    guaranteed_before += quantity
                if max(v[1] for v in differences) >= 0:
                    possible_before += quantity
            # possible_before includes self and ties; no ID tie-break is invented.
            per_pattern[(group,pattern)] = {
                'comparison_group':group_id, 'comparison_population':n,
                'best_rank_bound':1+guaranteed_before,
                'worst_rank_bound':possible_before,
                'strictly_lower_priority_guaranteed':n-possible_before,
                'priority_is_fully_resolved':1+guaranteed_before == possible_before,
            }
        summaries.append({'id':group_id,'stage':stage,'applicable_families':[f for f,a in zip(FAMILIES,applicable) if a],
                          'targets':n,'evidence_patterns':len(counts),'weight_vertices_checked':len(vertices)})

    results = []
    for key,group,pattern,coverage in items:
        interval = coverage['score_interval']
        results.append({'contract_id':key,'stage':group[0], **per_pattern[(group,pattern)],
                        'confirmed_families':[f for f,s in zip(FAMILIES,pattern) if s == DETECTED],
                        'unknown_families':[f for f,s in zip(FAMILIES,pattern) if s == UNKNOWN],
                        'central_weighted_count_interval':dict(interval),
                        'complete_count':coverage['complete_score'],
                        'review_route':'REVISAR_SENALES_CONFIRMADAS' if interval['min'] else
                            'COMPLETAR_EVIDENCIA' if coverage['unevaluable_families'] else 'SIN_SENAL_OBSERVADA',
                        'incomplete_indicator_evidence':coverage['evaluated_indicators'] < coverage['applicable_indicators'],
                        'publication_authorized':False})
    return {'policy':POLICY,'methodology':methodology(),'input_canonical_sha256':digest(report),
            'snapshot_cut':report.get('snapshot_cut'),'cohort_canonical_sha256':reference,
            'groups':summaries,'targets':len(results),'results':results,
            'review_route_counts':dict(Counter(r['review_route'] for r in results)),
            'fully_resolved_priorities':sum(r['priority_is_fully_resolved'] for r in results),
            'central_weights_changed':False,'weights_calibrated':False,
            'database_generation_consistency_verified':False,
            'input_declares_generation_consistency':report.get('database_generation_consistency_verified') is True,
            'historical_training_eligible':False,'model_index':None,'publication_authorized':False,
            'limitations':['Rank bounds are conservative and need not be jointly attainable.',
                           'Sensitivity box is an engineering assumption, not calibrated uncertainty.',
                           'Comparison uses the supplied cohort only, not all SECOP.',
                           'Evidence completeness and weight robustness do not establish corruption.']}
