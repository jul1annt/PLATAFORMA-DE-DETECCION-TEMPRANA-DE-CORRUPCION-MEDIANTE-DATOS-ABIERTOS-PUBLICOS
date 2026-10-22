"""Offline descriptive assessment; no database, ML, network or publication imports."""
import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

COMPONENTS = {'OUTLIER': 'max_score_outlier', 'DUPLICADO_CORTO': 'max_score_duplicado',
              'ABUSO_DIRECTO': 'score_directo'}


def number(value):
    if isinstance(value, bool) or value is None:
        raise ValueError('Se requiere número finito no negativo')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('Número inválido') from exc
    if not result.is_finite() or result < 0:
        raise ValueError('Se requiere número finito no negativo')
    return result


def weights(value):
    result = {key: number(value[key]) for key in COMPONENTS}
    if any(x > Decimal('999.99') for x in result.values()):
        raise ValueError('Peso fuera de escala del sistema legado')
    return result


def classification(score):
    return 'ALTO' if score >= 5 else 'MEDIO' if score >= 2 else 'BAJO'


def score(row, factors):
    return sum((number(row[field]) * factors[key] for key, field in COMPONENTS.items()), Decimal(0))


def assess(payload):
    rows = payload['rows']
    if not isinstance(rows, list) or not rows or len(rows) > 2000:
        raise ValueError('Seleccionar entre 1 y 2000 resultados existentes')
    configured = weights(payload['configured_weights'])
    baseline = [score(row, configured) for row in rows]
    contributions = {key: sum((number(row[field]) * configured[key] for row in rows), Decimal(0))
                     for key, field in COMPONENTS.items()}
    total = sum(contributions.values(), Decimal(0))
    mismatches, changed_since_run = 0, 0
    for row in rows:
        applied = weights(row['pesos_aplicados'])
        actual = score(row, applied)
        # Legacy computes using float and stores a score rounded to two places.
        mismatches += (abs(actual - number(row['score_final'])) > Decimal('.011')
                       or classification(actual) != row['clasificacion_riesgo'])
        changed_since_run += applied != configured
    sensitivity = []
    for key in COMPONENTS:
        for factor in (Decimal('.8'), Decimal('1.2')):
            changed = {**configured, key: configured[key] * factor}
            transitions = Counter()
            for row, original in zip(rows, baseline):
                transitions[(classification(original), classification(score(row, changed)))] += 1
            flips = sum(n for (before, after), n in transitions.items() if before != after)
            sensitivity.append({'component': key, 'factor': str(factor), 'classification_changes': flips,
                                'fraction': flips / len(rows),
                                'transitions': {f'{a}->{b}': n for (a, b), n in sorted(transitions.items())}})
    return {'assessment_version': 'legacy-weight-descriptive-v1',
            'scope': payload['scope'], 'rows': len(rows),
            'configured_weights': {k: str(v) for k, v in configured.items()},
            'classification_recomputed_with_current_weights': dict(Counter(map(classification, baseline))),
            'stored_result_mismatches_at_applied_weights': mismatches,
            'rows_with_applied_weights_different_from_current': changed_since_run,
            'weighted_contribution_share': {k: float(v / total) if total else None for k, v in contributions.items()},
            'observed_component_ranges': {key: {'min': str(min(number(r[field]) for r in rows)),
                                                'max': str(max(number(r[field]) for r in rows))}
                                          for key, field in COMPONENTS.items()},
            'one_factor_sensitivity': sensitivity,
            'limitations': ['Muestra por clave primaria, no aleatoria ni representativa.',
                           'Puede incluir varios cortes y ejecuciones; no es prevalencia poblacional.',
                           'Sensibilidad descriptiva; no mide precisión, causalidad o detección de corrupción.',
                           'Los ceros históricos no prueban cobertura completa de cada indicador.',
                           'No recomienda pesos óptimos ni calibra umbrales.'],
            'database_writes': False, 'training_performed': False, 'publication_changed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    report = assess(json.loads(raw))
    report['input_sha256'] = hashlib.sha256(raw).hexdigest()
    report['assessment_code_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(report, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps({'rows': report['rows'], 'stored_result_mismatches': report['stored_result_mismatches_at_applied_weights'],
                      'report': str(args.output)}))


if __name__ == '__main__':
    main()
