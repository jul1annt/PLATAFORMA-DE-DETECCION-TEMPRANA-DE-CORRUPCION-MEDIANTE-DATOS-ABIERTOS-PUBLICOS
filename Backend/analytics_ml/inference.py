"""Portable linear PU ensemble: JSON only, standard library only."""
from __future__ import annotations

import math
from .runtime import prediction_code_sha256
from modules.motor_riesgo.domain import FEATURE_VERSION, PREDICTION_POLICY, NUMERIC, CATEGORICAL, REFERENCES, digest, features, percentile, identity_reasons, stage_time_reasons


def vector(values: dict, transform: dict) -> list[float]:
    output = []
    for name in transform['numeric']:
        value = values.get(name)
        filled = transform['median'][name] if value is None else float(value)
        output.extend(((filled - transform['mean'][name]) / transform['scale'][name], float(value is None)))
    for name in CATEGORICAL:
        vocabulary = transform['categories'][name]
        value = values.get(name)
        output.extend(float(value == item) for item in vocabulary)
        output.append(float(value not in vocabulary))
    return output


def validate_artifact(artifact: dict) -> None:
    body = {k: v for k, v in artifact.items() if k != 'sha256'}
    if (artifact.get('sha256') != digest(body) or artifact.get('feature_version') != FEATURE_VERSION
            or artifact.get('prediction_policy') != PREDICTION_POLICY
            or artifact.get('prediction_code_sha256') != prediction_code_sha256()):
        raise ValueError('Artefacto o versión de variables inválidos')
    if artifact.get('positive_target') != 'CORRUPCION':
        raise ValueError('Objetivo positivo incompatible con el modelo de corrupción')
    stage = artifact.get('stage')
    if stage not in NUMERIC or tuple(artifact['transform']['numeric']) != NUMERIC[stage]:
        raise ValueError('Variables incompatibles con la etapa')
    transform = artifact['transform']
    size = len(NUMERIC[stage]) * 2 + sum(len(transform['categories'][n]) + 1 for n in CATEGORICAL)
    if not artifact.get('members') or not artifact.get('reference') or artifact['reference'] != sorted(artifact['reference']):
        raise ValueError('Ensamble o población de referencia inválidos')
    for member in artifact['members']:
        if len(member['coef']) != size or not all(math.isfinite(float(v)) for v in [*member['coef'], member['intercept']]):
            raise ValueError('Coeficientes inválidos')
    if 'linear_coef' in artifact:
        expected = [sum(m['coef'][i] for m in artifact['members']) / len(artifact['members']) for i in range(size)]
        intercept = sum(m['intercept'] for m in artifact['members']) / len(artifact['members'])
        if len(artifact['linear_coef']) != size or artifact['linear_coef'] != expected or artifact.get('linear_intercept') != intercept:
            raise ValueError('El ensamble compilado no coincide')
    if not all(math.isfinite(float(x)) for x in artifact['reference']):
        raise ValueError('Referencia inválida')
    for n in NUMERIC[stage]:
        if not all(math.isfinite(float(transform[k][n])) for k in ('median', 'mean', 'scale')) or transform['scale'][n] <= 0:
            raise ValueError('Transformación inválida')


def raw_score(artifact: dict, values: dict) -> tuple[float, list[dict]]:
    x = vector(values, artifact['transform'])
    coefficients = artifact.get('linear_coef')
    if coefficients is None:
        coefficients = [sum(m['coef'][i] for m in artifact['members']) / len(artifact['members']) for i in range(len(x))]
    intercept = artifact.get('linear_intercept')
    if intercept is None:
        intercept = sum(m['intercept'] for m in artifact['members']) / len(artifact['members'])
    labels = []
    for n in artifact['transform']['numeric']:
        labels.extend((n, n + ':faltante'))
    for n in CATEGORICAL:
        labels.extend(n + ':' + item for item in artifact['transform']['categories'][n])
        labels.append(n + ':desconocida')
    contributions = [{'variable': n, 'contribution': round(c * v, 8)} for n, c, v in zip(labels, coefficients, x)]
    return intercept + sum(c * v for c, v in zip(coefficients, x)), sorted(contributions, key=lambda a: abs(a['contribution']), reverse=True)[:5]


class PreparedPredictor:
    """Compile sparse categorical lookup once, instead of constructing dense
    vectors and averaging 25 estimators for every row in a multi-million cut.
    """
    def __init__(self, artifact):
        validate_artifact(artifact)
        self.artifact = artifact
        members = artifact['members']
        size = len(members[0]['coef'])
        self.coef = artifact.get('linear_coef') or [sum(m['coef'][i] for m in members) / len(members) for i in range(size)]
        self.intercept = artifact.get('linear_intercept')
        if self.intercept is None:
            self.intercept = sum(m['intercept'] for m in members) / len(members)
        self.categories = {}
        offset = 2 * len(artifact['transform']['numeric'])
        for name in CATEGORICAL:
            vocabulary = artifact['transform']['categories'][name]
            self.categories[name] = ({v: self.coef[offset+i] for i,v in enumerate(vocabulary)},self.coef[offset+len(vocabulary)])
            offset += len(vocabulary)+1

    def score(self, values):
        transform = self.artifact['transform']
        contributions = []
        for i,name in enumerate(transform['numeric']):
            value = values.get(name)
            filled = transform['median'][name] if value is None else float(value)
            contributions.extend(((name,self.coef[2*i]*((filled-transform['mean'][name])/transform['scale'][name])),
                                  (name+':faltante',self.coef[2*i+1]*float(value is None))))
        for name in CATEGORICAL:
            mapping,unknown = self.categories[name]
            value = values.get(name)
            contributions.append((name+':'+str(value) if value in mapping else name+':desconocida',mapping.get(value,unknown)))
        score = self.intercept + sum(v for _,v in contributions)
        signals = sorted(({'variable':n,'contribution':round(v,8)} for n,v in contributions),key=lambda x:abs(x['contribution']),reverse=True)[:5]
        return score,signals


def predict(artifact: dict, observation: dict, scorer=None) -> dict:
    values, reasons = features(observation, artifact['stage'])
    reasons.extend(observation.get('capture_reasons', []))
    temporal_reasons = stage_time_reasons(observation)
    reasons.extend(temporal_reasons)
    reasons.extend('fuera_de_referencia:' + n for n in CATEGORICAL if values.get(n) is not None and values[n] not in artifact['transform']['categories'][n])
    coverage = sum(v is not None for v in values.values()) / len(values)
    required = ('log_presupuesto', 'categoria', 'modalidad')
    if artifact['stage'] == 'ADJUDICACION':
        required += ('log_adjudicado',)
    metadata = {'stage': artifact['stage'], 'model_version': artifact['version'],
            'values': values, 'provenance': {k: observation.get(k) for k in ('source_id', 'source_row_id', 'process_id', 'lot_id', 'award_id', 'source_url', 'snapshot_sha256')},
            'feature_version': FEATURE_VERSION, 'prediction_at': observation['prediction_at'], 'references': REFERENCES,
            'observed': observation.get('observed', {}), 'context': observation.get('context', {}),
            'temporal_scope': observation.get('temporal_scope'), 'stage_event_at': observation.get('stage_event_at'),
            'interpretation': 'Prioridad relativa de revisión; no es probabilidad ni prueba de corrupción.'}
    if identity_reasons(observation, artifact['stage']) or temporal_reasons:
        return {**metadata, 'index': None, 'coverage': coverage, 'reasons': reasons, 'signals': []}
    if any(values.get(n) is None for n in required):
        return {**metadata, 'index': None, 'coverage': coverage, 'reasons': reasons + ['variables_esenciales_ausentes'], 'signals': []}
    score, signals = (scorer or (lambda v: raw_score(artifact,v)))(values)
    if not math.isfinite(score):
        return {**metadata, 'index': None, 'coverage': coverage, 'reasons': reasons + ['resultado_numerico_no_evaluable'], 'signals': []}
    return {**metadata, 'index': percentile(artifact['reference'], score), 'coverage': coverage, 'reasons': reasons, 'signals': signals}
