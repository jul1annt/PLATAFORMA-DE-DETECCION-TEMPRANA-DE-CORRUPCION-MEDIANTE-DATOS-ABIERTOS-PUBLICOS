"""Audit registered response counters; never infer submitted or valid bids.

Official SECOP II metadata distinguishes responses, invitations and interest.
These observations are descriptive context, not the OFERENTE_UNICO predictor.
"""
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from .domain import official_id, digest
from .method_reference import direct_method

POLICY = 'secop-registered-responses-context-v1'
DATASET = 'p6dx-8zbt'
FIELDS = ('proveedores_invitados', 'proveedores_con_invitacion', 'proveedores_que_manifestaron',
          'respuestas_al_procedimiento', 'respuestas_externas', 'conteo_de_respuestas_a_ofertas',
          'proveedores_unicos_con', 'numero_de_lotes')
MAX_COUNT = 2147483647


def metric(value):
    if value is None:
        return {'state': 'AUSENTE', 'value': None}
    if not isinstance(value, bool):
        try:
            result = Decimal(str(value))
            if result.is_finite() and 0 <= result <= MAX_COUNT and result == result.to_integral_value():
                integer = int(result)
                return {'state': 'CERO' if integer == 0 else 'UNO' if integer == 1 else 'MULTIPLE', 'value': integer}
        except (ValueError, InvalidOperation):
            pass
    return {'state': 'INVALIDO', 'value': None}


def observe(row, dataset_id):
    metrics = {field: metric(row.get(field)) for field in FIELDS}
    unique = metrics['proveedores_unicos_con']
    lots = metrics['numero_de_lotes']['value']
    verified_source = dataset_id == DATASET
    identity = (type(row.get('source_id')) is int and row['source_id'] > 0
                and type(row.get('global_unit_rows_up_to_two')) is int and row['global_unit_rows_up_to_two'] == 1
                and all(official_id(row.get(key)) for key in ('source_row_id', 'process_id', 'award_id'))
                and str(row.get('awarded') or '').strip().upper() in {'SI', 'SÍ', 'TRUE', '1'})
    pattern = ('NO_EVALUABLE' if not verified_source or unique['value'] is None else
               'CERO_PROVEEDORES_DECLARADOS_NO_ACREDITA_CERO_OFERENTES' if unique['value'] == 0 else
               'UN_PROVEEDOR_CON_RESPUESTA_DECLARADO' if unique['value'] == 1 else
               'VARIOS_PROVEEDORES_CON_RESPUESTA_DECLARADOS')
    direct = direct_method(row.get('method'))
    return {'contract_id': row.get('contract_id'), 'source_id': row.get('source_id'),
            'source_row_id': row.get('source_row_id'), 'process_id': row.get('process_id'),
            'award_id': row.get('award_id'), 'metrics': metrics, 'response_pattern': pattern,
            'source_schema_recognized': verified_source, 'operation_identity_admissible': bool(identity),
            'modality_class': 'DIRECTA_DEL_DICCIONARIO' if direct is True else
                              'COMPETITIVA_DEL_DICCIONARIO' if direct is False else 'NO_VERIFICADA',
            'lot_scope': 'UN_LOTE_DECLARADO' if lots == 1 else 'VARIOS_LOTES_SIN_ASIGNACION_POR_ADJUDICACION' if lots and lots > 1
                         else 'CERO_O_LOTES_DESCONOCIDOS_NO_EQUIVALE_A_LOTE_UNICO',
            'actual_bidders': None, 'model_values': {}, 'scoring_eligible': False,
            'training_eligible': False, 'publication_authorized': False,
            'reason': 'contadores_de_respuestas_no_acreditan_ofertas_presentadas_validas_ni_concurrencia_por_lote'}


def assess(payload):
    scope, rows = payload['scope'], payload['rows']
    if (not isinstance(rows, list) or not 1 <= len(rows) <= 20000 or type(scope.get('rows')) is not int
            or scope['rows'] != len(rows) or scope.get('temporal_scope') != 'current_cut_descriptive_not_stage_prediction'):
        raise ValueError('Se requiere una proyección acotada y descriptiva del corte')
    ids = [row.get('contract_id') for row in rows]
    if any(type(key) is not int or key < 1 for key in ids) or len(ids) != len(set(ids)):
        raise ValueError('Identificadores locales de fila inválidos o repetidos')
    source_datasets = scope['source_datasets']
    results = [observe(row, source_datasets.get(str(row.get('source_id')))) for row in rows]
    populations = defaultdict(list)
    for raw, result in zip(rows, results):
        populations['ALL_SELECTED_ROWS'].append(result)
        labels = raw.get('selection_groups', [])
        if not isinstance(labels, list) or any(not isinstance(label, str) or not label for label in labels):
            raise ValueError('Grupos de selección inválidos')
        if len(labels) != len(set(labels)) or 'ALL_SELECTED_ROWS' in labels:
            raise ValueError('Grupos repetidos o reservados')
        for label in labels: populations[label].append(result)
    summary = {}
    for name, selected in sorted(populations.items()):
        processes = defaultdict(list)
        for row in selected:
            if type(row['source_id']) is int and row['source_id'] > 0 and official_id(row['process_id']):
                processes[(row['source_id'], official_id(row['process_id']))].append(row)
        counter_states = Counter()
        for members in processes.values():
            observations = {(row['metrics']['proveedores_unicos_con']['state'],
                             row['metrics']['proveedores_unicos_con']['value']) for row in members}
            counter_states[next(iter(observations))[0] if len(observations) == 1 else 'DISCREPANTE_O_INCOMPLETO_ENTRE_FILAS_OBSERVADAS'] += 1
        summary[name] = {'selected_rows': len(selected),
                         'operation_identity_admissible_rows': sum(row['operation_identity_admissible'] for row in selected),
                         'recognized_dataset_rows': sum(row['source_schema_recognized'] for row in selected),
                         'modality_counts': dict(Counter(row['modality_class'] for row in selected)),
                         'response_patterns': dict(Counter(row['response_pattern'] for row in selected)),
                         'field_states': {field: dict(Counter(row['metrics'][field]['state'] for row in selected)) for field in FIELDS},
                         'observed_processes': len(processes), 'process_unique_counter_states': dict(counter_states),
                         'process_consistency_scope': 'selected_rows_only_not_complete_process_frame'}
    return {'policy': POLICY, 'scope': scope, 'source_field': 'proveedores_unicos_con',
            'actual_bidder_field_verified': False, 'actual_bidder_fallback_enabled': False,
            'summary': summary, 'results': results, 'input_canonical_sha256': digest(payload),
            'training_eligible': False, 'publication_authorized': False, 'weight_changes': False,
            'limitations': ['Respuestas al procedimiento pueden incluir respuestas de la entidad según la metadata actual.',
                            'Proveedores con respuestas no acreditan ofertas presentadas ni válidas.',
                            'Contadores de proceso no proporcionan competencia de cada lote/adjudicación.',
                            'La muestra seleccionada no es un censo de SECOP ni un marco completo de cada proceso.',
                            'Cero, ausencia e invalidez se conservan separados; no hay sustitución entre contadores.']}
