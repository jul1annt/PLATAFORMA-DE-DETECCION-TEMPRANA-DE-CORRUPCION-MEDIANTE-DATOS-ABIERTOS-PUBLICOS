"""Pure descriptive baseline. Unknown evidence is not a negative finding."""
from decimal import Decimal, InvalidOperation
import unicodedata

POLICY = 'binary-family-coverage-v1'
DETECTED = 'DETECTADA'
CLEAR = 'SIN_SENAL'
UNKNOWN = 'NO_EVALUABLE'
NOT_APPLICABLE = 'NO_APLICA'

# Explicit local dictionary; an unrecognized modality is not assumed competitive.
COMPETITIVE = frozenset({
    'LICITACION PUBLICA', 'LICITACION PUBLICA OBRA PUBLICA',
    'SELECCION ABREVIADA', 'SELECCION ABREVIADA DE MENOR CUANTIA',
    'SELECCION ABREVIADA SUBASTA INVERSA', 'CONCURSO DE MERITOS',
    'CONCURSO DE MERITOS ABIERTO', 'CONCURSO DE MERITOS CON LISTA CORTA',
    'MINIMA CUANTIA',
})
NONCOMPETITIVE = frozenset({'CONTRATACION DIRECTA', 'CONTRATACION DIRECTA (LEY 1150 DE 2007)'})


def count(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() and result >= 0 and result == result.to_integral_value() else None


def finding(indicator, status, *, reason=None, observed=None):
    return {'indicator': indicator, 'status': status,
            'detected': True if status == DETECTED else False if status == CLEAR else None,
            'reason': reason, 'observed': observed}


def summarize(stage, indicators):
    """Each family contributes at most one unit, irrespective of its indicator count."""
    groups = {'IMPORTE_ATIPICO': ['IMPORTE_ATIPICO'], 'COMPETENCIA': ['OFERENTE_UNICO'],
              'CONCENTRACION_REITERACION': ['DIRECTAS_90D', 'REITERACION_30D']}
    families = {}
    for family, names in groups.items():
        states = [indicators[name]['status'] for name in names]
        applicable = [state for state in states if state != NOT_APPLICABLE]
        state = (NOT_APPLICABLE if not applicable else DETECTED if DETECTED in applicable
                 else UNKNOWN if UNKNOWN in applicable else CLEAR)
        families[family] = {'status': state, 'weight': 1,
                            'contribution': 1 if state == DETECTED else 0 if state == CLEAR else None,
                            'indicators': names}
    applicable = sum(f['status'] != NOT_APPLICABLE for f in families.values())
    evaluated = sum(f['status'] in (DETECTED, CLEAR) for f in families.values())
    detected = sum(f['status'] == DETECTED for f in families.values())
    unknown = applicable - evaluated
    return {'policy': POLICY, 'stage': stage, 'indicators': indicators, 'families': families,
            'confirmed_signal_count': detected, 'applicable_families': applicable,
            'evaluated_families': evaluated, 'unevaluable_families': unknown,
            'family_coverage': evaluated / applicable if applicable else None,
            'applicable_indicators': sum(i['status'] != NOT_APPLICABLE for i in indicators.values()),
            'evaluated_indicators': sum(i['status'] in (DETECTED, CLEAR) for i in indicators.values()),
            'complete_score': detected if applicable and not unknown else None,
            'score_interval': {'min': detected, 'max': detected + unknown},
            'interpretation': 'Conteo descriptivo de familias; intervalo por datos no evaluables, no probabilidad ni intervalo estadístico.',
            'publication_authorized': False}


def baseline_coverage(values, stage, iqr=None, *, competition_semantics_verified=False):
    if stage not in ('CONVOCATORIA', 'ADJUDICACION'):
        raise ValueError('Etapa inválida')
    if type(competition_semantics_verified) is not bool:
        raise ValueError('Verificación semántica debe ser booleana')
    result = iqr or {'detected': None, 'reason': 'iqr_no_calculado'}
    detected = result.get('detected')
    if detected is not None and type(detected) is not bool:
        raise ValueError('Detección IQR debe ser booleana o desconocida')
    indicators = {'IMPORTE_ATIPICO': finding('IMPORTE_ATIPICO', UNKNOWN if detected is None else DETECTED if detected else CLEAR,
                                           reason=result.get('reason'), observed=result)}
    if stage == 'CONVOCATORIA':
        for name in ('OFERENTE_UNICO', 'DIRECTAS_90D', 'REITERACION_30D'):
            indicators[name] = finding(name, NOT_APPLICABLE, reason='indicador_de_adjudicacion')
        return summarize(stage, indicators)
    method = ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(values.get('modalidad') or '').upper())
                             if not unicodedata.combining(c)).split())
    bidders = count(values.get('oferentes'))
    if method in NONCOMPETITIVE:
        competition = finding('OFERENTE_UNICO', NOT_APPLICABLE, reason='modalidad_no_competitiva')
    elif method not in COMPETITIVE:
        competition = finding('OFERENTE_UNICO', UNKNOWN, reason='modalidad_no_verificada')
    elif not competition_semantics_verified:
        competition = finding('OFERENTE_UNICO', UNKNOWN, reason='semantica_oferentes_no_verificada')
    elif bidders is None or bidders == 0:
        competition = finding('OFERENTE_UNICO', UNKNOWN, reason='oferentes_ausentes_o_invalidos')
    else:
        competition = finding('OFERENTE_UNICO', DETECTED if bidders == 1 else CLEAR,
                              observed={'oferentes': str(bidders), 'modalidad': method})
    indicators['OFERENTE_UNICO'] = competition
    for name, field, threshold in (('DIRECTAS_90D', 'directas_90d', 3), ('REITERACION_30D', 'reiteraciones_30d', 2)):
        observed = count(values.get(field))
        indicators[name] = finding(name, UNKNOWN if observed is None else DETECTED if observed >= threshold else CLEAR,
                                   reason='conteo_ausente_o_invalido' if observed is None else None,
                                   observed={'value': str(observed) if observed is not None else None, 'threshold': threshold})
    return summarize(stage, indicators)
