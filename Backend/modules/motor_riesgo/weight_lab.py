"""Offline descriptive normalization lab; no fitting, labels, DB or publication."""
from bisect import bisect_left, bisect_right
from decimal import Decimal, InvalidOperation, localcontext
from itertools import groupby
from math import sqrt
import hashlib
import json

FIELDS = {'OUTLIER': 'max_score_outlier', 'DUPLICADO_CORTO': 'max_score_duplicado',
          'ABUSO_DIRECTO': 'score_directo'}
FRACTIONS = (Decimal('.01'), Decimal('.05'), Decimal('.10'))
POLICY = 'legacy-normalization-lab-v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def number(value):
    if value is None or isinstance(value, bool):
        raise ValueError('Componente ausente o inválido')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('Componente inválido') from exc
    if not result.is_finite() or result < 0:
        raise ValueError('Componente no finito o negativo')
    return result


def top_weights(scores, fraction):
    """Fractional inclusion at tied boundaries; independent of row identifiers."""
    fraction = number(fraction)
    if not scores or not 0 < fraction <= 1:
        raise ValueError('Ranking vacío o fracción inválida')
    result = [Decimal(0)] * len(scores)
    remaining = Decimal(len(scores)) * fraction
    for _, block in groupby(sorted(range(len(scores)), key=scores.__getitem__, reverse=True), key=scores.__getitem__):
        indices = list(block)
        boundary = remaining < len(indices)
        inclusion = remaining / len(indices) if boundary else Decimal(1)
        for i in indices:
            result[i] = inclusion
        if boundary:
            break
        remaining -= len(indices)
        if remaining == 0:
            break
    return result


def overlap(first, second, fraction):
    if len(first) != len(second):
        raise ValueError('Las prioridades deben corresponder al mismo universo')
    fraction = number(fraction)
    a, b = top_weights(first, fraction), top_weights(second, fraction)
    return float(sum(min(x, y) for x, y in zip(a, b)) / (Decimal(len(a)) * fraction))


def ranks(values):
    result = [0.] * len(values)
    start = 0
    for _, block in groupby(sorted(range(len(values)), key=values.__getitem__), key=values.__getitem__):
        indices = list(block)
        rank = (start + 1 + start + len(indices)) / 2
        for i in indices:
            result[i] = rank
        start += len(indices)
    return result


def spearman(first, second):
    if len(first) != len(second) or not first:
        raise ValueError('Vectores de ranking incompatibles')
    a, b = ranks(first), ranks(second)
    mean = (len(a) + 1) / 2
    numerator = sum((x - mean) * (y - mean) for x, y in zip(a, b))
    denominator = sqrt(sum((x - mean) ** 2 for x in a) * sum((y - mean) ** 2 for y in b))
    return max(-1., min(1., numerator / denominator)) if denominator else None


def freeze_reference(columns, scope):
    result = {'policy': 'frozen-legacy-component-ecdf-v1', 'scope_sha256': digest(scope),
              'n': len(next(iter(columns.values()))),
              'components': {name: [str(v) for v in sorted(values)] for name, values in columns.items()},
              'zero_rule': 'El cero legado permanece cero; no acredita cobertura del indicador.'}
    result['sha256'] = digest(result)
    return result


def reference_columns(reference):
    if (reference.get('sha256') != digest({k: v for k, v in reference.items() if k != 'sha256'})
            or reference.get('policy') != 'frozen-legacy-component-ecdf-v1'
            or type(reference.get('n')) is not int or not 1 <= reference['n'] <= 100000
            or set(reference.get('components', {})) != set(FIELDS)):
        raise ValueError('Referencia congelada inválida')
    columns = {key: [number(v) for v in reference['components'][key]] for key in FIELDS}
    if any(len(v) != reference['n'] or v != sorted(v) for v in columns.values()):
        raise ValueError('Referencia desordenada o incompleta')
    return columns


def empirical_transform(columns, reference):
    frozen = reference_columns(reference)
    return {key: [Decimal(0) if value == 0 else
                  (Decimal(bisect_left(frozen[key], value)) + Decimal(bisect_right(frozen[key], value)))
                  / (2 * len(frozen[key])) for value in values] for key, values in columns.items()}


def weighted_scores(columns, weights):
    return [sum(columns[key][i] * weights[key] for key in FIELDS)
            for i in range(len(next(iter(columns.values()))))]


def summary(scores):
    ordered = sorted(scores)
    return {'min': str(ordered[0]), 'median': str(ordered[len(ordered) // 2]),
            'p95_nearest_order': str(ordered[min(len(ordered) - 1, int(len(ordered) * .95))]),
            'max': str(ordered[-1]), 'distinct_scores': len(set(scores)),
            'zero_rows': sum(x == 0 for x in scores)}


def assess(payload):
    with localcontext() as context:
        context.prec = 28
        return _assess(payload)


def _assess(payload):
    rows = payload['rows']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100000:
        raise ValueError('Se requieren entre 1 y 100000 resultados')
    if (payload['scope'].get('census') is not True or type(payload['scope'].get('expected_rows')) is not int
            or payload['scope']['expected_rows'] != len(rows)):
        raise ValueError('El alcance debe acreditar el censo delimitado y su cantidad')
    identifiers = [r.get('id') for r in rows]
    if (any(not isinstance(key, str) or not key.strip() for key in identifiers)
            or len(set(identifiers)) != len(rows)):
        raise ValueError('El censo requiere claves de resultado únicas y no vacías')
    columns = {key: [number(r[field]) for r in rows] for key, field in FIELDS.items()}
    if any(value > 10 for key in ('DUPLICADO_CORTO', 'ABUSO_DIRECTO') for value in columns[key]):
        raise ValueError('Componente legado fuera de su escala documentada; revisar antes de normalizar')
    weights = {key: number(payload['configured_weights'][key]) for key in FIELDS}
    if any(value > Decimal('999.99') for value in weights.values()):
        raise ValueError('Peso fuera de escala')
    equal = {key: Decimal(1) for key in FIELDS}
    bounded = {key: [v / (1 + v) if key == 'OUTLIER' else v / 10 for v in column]
               for key, column in columns.items()}
    reference = freeze_reference(columns, payload['scope'])
    empirical = empirical_transform(columns, reference)
    variants = {'LEGADO': (columns, weights), 'ESCALA_ORIGINAL_PESOS_IGUALES': (columns, equal),
                'ACOTADO_PESOS_LEGADOS': (bounded, weights), 'ACOTADO_PESOS_IGUALES': (bounded, equal),
                'ECDF_PESOS_IGUALES': (empirical, equal)}
    scores = {name: weighted_scores(vectors, factors) for name, (vectors, factors) in variants.items()}
    results = {}
    for name, (vectors, factors) in variants.items():
        contributions = {key: sum(vectors[key]) * factors[key] for key in FIELDS}
        total = sum(contributions.values())
        results[name] = {'score_summary': summary(scores[name]),
                         'component_contribution_share': {key: float(v / total) if total else None for key, v in contributions.items()},
                         'top_overlap_with_legacy': {str(f): overlap(scores['LEGADO'], scores[name], f) for f in FRACTIONS},
                         'spearman_with_legacy': spearman(scores['LEGADO'], scores[name])}
        if name in ('ACOTADO_PESOS_IGUALES', 'ECDF_PESOS_IGUALES'):
            results[name]['top5_weight_sensitivity'] = []
            for key in FIELDS:
                for factor in (Decimal('.8'), Decimal('1.2')):
                    changed = weighted_scores(vectors, {**factors, key: factors[key] * factor})
                    results[name]['top5_weight_sensitivity'].append(
                        {'component': key, 'factor': str(factor), 'overlap': overlap(scores[name], changed, Decimal('.05'))})
    report = {'policy': POLICY, 'decimal_precision': 28, 'scope': payload['scope'], 'rows': len(rows),
              'reference_sha256': reference['sha256'], 'variants': results,
              'component_spearman': {f'{a}:{b}': spearman(columns[a], columns[b]) for a, b in
                                     [('OUTLIER', 'DUPLICADO_CORTO'), ('OUTLIER', 'ABUSO_DIRECTO'), ('DUPLICADO_CORTO', 'ABUSO_DIRECTO')]},
              'bounded_formulas': {'OUTLIER': 's/(1+s)', 'DUPLICADO_CORTO': 's/10', 'ABUSO_DIRECTO': 's/10'},
              'ecdf_formula': 'Cero permanece cero; positivos: (cantidad menor + 0.5*cantidad igual)/n de referencia congelada.',
              'ranking': 'Masa fraccionaria en empates; coincidencia=sum(min(inclusion_a,inclusion_b))/(n*fraccion).',
              'limitations': ['Censo de resultados legados por proveedor de una ejecución; no universo completo de contratos.',
                             'Los ceros históricos no acreditan ausencia de riesgo ni cobertura de los indicadores.',
                             'Estos componentes no equivalen a las familias corregidas por operación y etapa.',
                             'Referencia congelada del corte para descripción; no disponible retrospectivamente en convocatoria.',
                             'Estabilidad y correlación no demuestran precisión, causalidad ni calibración judicial.',
                             'No se selecciona una alternativa por su coincidencia con el legado.'],
              'database_accessed': False, 'training_performed': False, 'publication_authorized': False}
    return report, reference
