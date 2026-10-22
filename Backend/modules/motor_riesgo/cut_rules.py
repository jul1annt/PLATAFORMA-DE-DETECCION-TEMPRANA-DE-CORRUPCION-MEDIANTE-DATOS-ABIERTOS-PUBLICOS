"""Current-cut descriptive rules. This is never a historical training snapshot."""
from collections import Counter
from datetime import date
from decimal import Decimal, localcontext
import re
from .baseline_coverage import baseline_coverage
from .domain import digest, official_id
from .rules import iqr_finding
from .weight_lab import number

POLICY = 'complete-cohort-current-cut-v1'
TEMPORAL_SCOPE = 'current_cut_descriptive_not_stage_prediction'


def assess(payload):
    with localcontext() as context:
        context.prec = 28
        return _assess(payload)


def _assess(payload):
    scope, rows = payload['scope'], payload['rows']
    if (scope.get('temporal_scope') != TEMPORAL_SCOPE or scope.get('full_selected_cohort') is not True
            or not isinstance(rows, list) or not 1 <= len(rows) <= 20000
            or type(scope.get('raw_peer_rows')) is not int or scope['raw_peer_rows'] != len(rows)):
        raise ValueError('Se requiere una cohorte completa del corte, sin presentarla como historia de etapa')
    selection = scope['selection']
    start, end = date.fromisoformat(selection['start']), date.fromisoformat(selection['end'])
    cut = date.fromisoformat(scope['snapshot_cut'])
    if (start.month, start.day, end.month, end.day, end.year) != (1, 1, 1, 1, start.year + 1):
        raise ValueError('La referencia requiere un periodo anual explícito')
    if (not re.fullmatch(r'(?:V\d+\.)?\d{8}', selection['category'])
            or selection['category'].endswith('00000000') or not selection['method'].strip()):
        raise ValueError('Categoría o modalidad no verificable')
    ids = [row.get('id') for row in rows]
    if any(type(key) is not int or key < 1 for key in ids) or len(set(ids)) != len(ids):
        raise ValueError('Identificadores locales de fila inválidos o duplicados')
    targets = scope['target_contract_ids']
    if (not isinstance(targets, list) or not targets or any(type(key) is not int for key in targets)
            or len(set(targets)) != len(targets) or not set(targets) <= set(ids)):
        raise ValueError('Los objetivos deben pertenecer a la cohorte completa')
    by_id, keys, reasons = {row['id']: row for row in rows}, {}, {}
    for row in rows:
        key = (row.get('fuente_id'), official_id(row.get('id_del_proceso')), official_id(row.get('id_adjudicacion')))
        why = None
        try:
            when = date.fromisoformat(row['fecha_publicacion_normalizada'])
        except (TypeError, ValueError, KeyError):
            raise ValueError('Fila sin fecha dentro de la cohorte declarada')
        if (not start <= when < end or row.get('modalidad_contratacion') != selection['method']
                or row.get('codigo_principal_de_categoria') != selection['category']):
            raise ValueError('La fila no pertenece a la categoría/modalidad/periodo declarado')
        if when > cut:
            why = 'publicacion_posterior_al_corte'
        elif type(key[0]) is not int or key[0] < 1 or not key[1] or not key[2] or not official_id(row.get('socrata_row_id')):
            why = 'identidad_incompleta'
        elif str(row.get('adjudicado') or '').strip().upper() not in {'SI', 'SÍ', 'TRUE', '1'}:
            why = 'sin_adjudicacion_confirmada'
        elif type(row.get('unit_rows_up_to_two')) is not int or row['unit_rows_up_to_two'] != 1:
            why = 'identidad_ambigua_o_no_comprobada'
        keys[row['id']], reasons[row['id']] = key, why
    counts = Counter(keys[key] for key in ids if reasons[key] is None)
    for key in ids:
        if reasons[key] is None and counts[keys[key]] > 1:
            reasons[key] = 'unidad_repetida_en_cohorte'
    amounts, exclusions = {}, Counter()
    for row in rows:
        key = row['id']
        if reasons[key]:
            exclusions[reasons[key]] += 1
            continue
        try:
            value = number(row.get('valor_total_adjudicacion'))
            if value <= 0:
                raise ValueError('Importe no positivo')
            amounts[key] = value
        except ValueError:
            reasons[key] = 'importe_ausente_o_invalido'
            exclusions[reasons[key]] += 1
    peers = list(amounts.values())
    template = iqr_finding(peers[0] if peers else None, peers)
    reference = {'category': selection['category'], 'method': selection['method'], 'year': start.year,
                 'n': len(peers), 'exclusions': dict(exclusions),
                 'peer_values_sha256': digest(sorted((keys[key], str(value)) for key, value in amounts.items())),
                 'iqr': {key: value for key, value in template.items() if key not in {'detected', 'value'}}}
    reference['sha256'] = digest(reference)
    results = []
    for key in targets:
        row = by_id[key]
        finding = dict(template)
        if key not in amounts:
            finding.update(detected=None, reason=reasons[key], value=None)
        else:
            value = amounts[key]
            finding['value'] = str(value)
            if template['detected'] is not None:
                finding['detected'] = value < Decimal(template['lower']) or value > Decimal(template['upper'])
        coverage = baseline_coverage({'modalidad': selection['method']}, 'ADJUDICACION', finding)
        results.append({'contract_id': key, 'source_id': row.get('fuente_id'), 'source_row_id': row.get('socrata_row_id'),
                        'process_id': row.get('id_del_proceso'), 'award_id': row.get('id_adjudicacion'),
                        'stage': 'ADJUDICACION', 'temporal_scope': TEMPORAL_SCOPE, 'training_eligible': False,
                        'reference_sha256': reference['sha256'], 'coverage': coverage})
    return {'policy': POLICY, 'scope': scope, 'reference': reference, 'results': results,
            'iqr_evaluable_targets': sum(row['coverage']['indicators']['IMPORTE_ATIPICO']['detected'] is not None for row in results),
            'complete_targets': sum(row['coverage']['complete_score'] is not None for row in results),
            'limitations': ['Importes reportados por SECOP, sin confirmar unidad monetaria y precio unitario mediante documentos físicos.',
                           'Referencia del corte actual; no información disponible al momento de adjudicar.',
                           'Solo se reconstruye IQR; no se reutilizan pares legados como conteos móviles corregidos.',
                           'Oferentes y concentraciones permanecen no evaluables cuando falta su evidencia.'],
            'training_performed': False, 'model_index': None, 'publication_authorized': False, 'database_accessed': False}
