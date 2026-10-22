"""Exploratory contract-result strata, without propagating supplier risk."""
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, localcontext
import re
import unicodedata
from .domain import official_id
from .weight_lab import number, overlap, spearman

POLICY = 'contract-result-strata-v1'


def label(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(value or '').upper())
                            if not unicodedata.combining(c)).split()) or 'SIN_MODALIDAD'


def dimensions(row):
    try:
        period = str(date.fromisoformat(row['publication_date']).year)
    except (KeyError, TypeError, ValueError):
        period = 'SIN_FECHA'
    match = re.fullmatch(r'(?:V\d+\.)?(\d{8})', str(row.get('category') or '').strip())
    sector = match[1][:2] if match and match[1] != '00000000' else 'SIN_UNSPSC_VERIFICABLE'
    return {'publication_year': period, 'method': label(row.get('method')), 'unspsc_segment': sector}


def identity_key(row):
    if type(row.get('source_id')) is not int or row['source_id'] < 1:
        return None, 'fuente_ausente_o_invalida'
    if not official_id(row.get('source_row_id')) or not official_id(row.get('process_id')):
        return None, 'identidad_secop_incompleta'
    if label(row.get('awarded')) not in {'SI', 'TRUE', '1'} or not official_id(row.get('award_id')):
        return None, 'sin_adjudicacion_identificable'
    if row.get('unit_rows_up_to_two') != 1 or type(row.get('unit_rows_up_to_two')) is not int:
        return None, 'unidad_ambigua_o_sin_comprobacion_global'
    return (row['source_id'], official_id(row['process_id']), official_id(row['award_id'])), None


def observed(row):
    try:
        iqr = number(row.get('iqr_score'))
        if type(row.get('iqr_detected')) is not bool or (not row['iqr_detected'] and iqr > 0):
            iqr = None
    except ValueError:
        iqr = None
    pair = None
    total, valid = row.get('legacy_pair_count'), row.get('valid_pair_count')
    if type(total) is int and type(valid) is int and 0 < valid <= total:
        try:
            value = number(row.get('verified_reiteration_score'))
            pair = value if value <= 10 else None
        except ValueError:
            pass
    return iqr, pair


def aggregate(rows):
    pairs = [observed(row) for row in rows]
    complete = [(a, b) for a, b in pairs if a is not None and b is not None]
    result = {'rows': len(rows), 'iqr_evaluable': sum(a is not None for a, _ in pairs),
              'iqr_detected': sum(a is not None and row['iqr_detected'] for row, (a, _) in zip(rows, pairs)),
              'reiteration_observed_with_verified_link': sum(b is not None for _, b in pairs),
              'reiteration_unknown': sum(b is None for _, b in pairs), 'joint_comparable_rows': len(complete),
              'comparison': None, 'comparison_abstention': 'menos_de_30_unidades_con_ambos_componentes'}
    if len(complete) < 30:
        return result
    raw = [a + Decimal('1.5') * b for a, b in complete]
    bounded_legacy = [a / (1 + a) + Decimal('1.5') * b / 10 for a, b in complete]
    bounded_equal = [a / (1 + a) + b / 10 for a, b in complete]
    result['comparison'] = {
        'unit': 'adjudicacion_identificada_con_dos_componentes_legados_observados',
        'bounded_legacy_top5_overlap': overlap(raw, bounded_legacy, Decimal('.05')),
        'bounded_equal_top5_overlap': overlap(raw, bounded_equal, Decimal('.05')),
        'bounded_equal_spearman': spearman(raw, bounded_equal),
        'component_spearman': spearman([a for a, _ in complete], [b for _, b in complete])}
    result['comparison_abstention'] = None
    return result


def assess(payload):
    with localcontext() as context:
        context.prec = 28
        return _assess(payload)


def _assess(payload):
    rows = payload['rows']
    if (payload['scope'].get('unit') != 'resultado_contrato_legado' or not isinstance(rows, list)
            or not 1 <= len(rows) <= 12000 or type(payload['scope'].get('selected_rows')) is not int
            or payload['scope']['selected_rows'] != len(rows)):
        raise ValueError('Se requiere una selección delimitada de resultados de contrato')
    ids = [row.get('result_id') for row in rows]
    if any(not isinstance(key, str) or not key.strip() for key in ids) or len(set(ids)) != len(ids):
        raise ValueError('Identificadores de resultado ausentes o duplicados')
    if any('score_directo' in row or 'score_final' in row for row in rows):
        raise ValueError('No trasladar puntuaciones agregadas de proveedor al contrato')
    identities = ([identity_key(row) for row in rows] if payload['scope'].get('enrichment_completed') is True
                  else [(None, 'comprobaciones_globales_pendientes') for _ in rows])
    counts = Counter(key for key, reason in identities if not reason)
    eligible, excluded = [], Counter()
    for row, (key, reason) in zip(rows, identities):
        if reason:
            excluded[reason] += 1
        elif counts[key] != 1:
            excluded['unidad_repetida_en_seleccion'] += 1
        else:
            eligible.append(row)
    groups = {name: defaultdict(list) for name in ('publication_year', 'method', 'unspsc_segment')}
    for row in eligible:
        for key, value in dimensions(row).items():
            groups[key][value].append(row)
    return {'policy': POLICY, 'scope': payload['scope'], 'input_rows': len(rows),
            'eligible_award_units': len(eligible), 'excluded_rows': sum(excluded.values()),
            'exclusions': dict(excluded), 'overall': aggregate(eligible),
            'strata': {dimension: {key: aggregate(group) for key, group in sorted(values.items())}
                       for dimension, values in groups.items()},
            'minimum_joint_rows': 30,
            'definitions': {'publication_year': 'Año de publicación, no año de sentencia ni adjudicación.',
                            'unspsc_segment': 'Dos primeros dígitos de código UNSPSC con formato de ocho dígitos; no sector institucional.',
                            'reiteration_unknown': 'No existe par comprobado o el vínculo no supera revisión de identidades/fechas; no significa ausencia.'},
            'limitations': ['Selección exploratoria por intervalos UUID; no garantiza representación de segmentos raros.',
                           'Metadatos del corte actual enlazados a resultados legados; no reconstrucción histórica de etapa.',
                           'Las fórmulas legadas no equivalen a las familias corregidas por operación.',
                           'Comparaciones condicionadas a ambos componentes observados; informar su cobertura.',
                           '30 unidades es un mínimo operativo de presentación, no suficiencia inferencial.',
                           'No se propaga riesgo de proveedor, no se calcula probabilidad o prevalencia de corrupción.'],
            'training_performed': False, 'publication_authorized': False, 'database_accessed': False}
