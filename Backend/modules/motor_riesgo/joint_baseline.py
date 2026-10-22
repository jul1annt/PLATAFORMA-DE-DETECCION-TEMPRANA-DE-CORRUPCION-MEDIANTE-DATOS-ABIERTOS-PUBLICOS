"""Compose descriptive families only after checking shared target facts.

Current-cut descriptions never become historical training observations. Matching
cut dates and target facts do not prove a common database generation; that limit
is explicit in every output. No supplier score is accepted as contract evidence.
"""
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
import unicodedata
from .baseline_coverage import baseline_coverage
from .cut_rules import assess as assess_iqr, TEMPORAL_SCOPE
from .rolling_evidence import assess as assess_rolling
from .domain import digest, official_id, instant
from .robust_priority import assess as assess_priority

POLICY = 'current-cut-joint-families-v1'


def _method(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(value or '').upper())
                             if not unicodedata.combining(c)).split())


def _same_amount(first, second):
    if isinstance(first, bool) or isinstance(second, bool):
        return type(first) is type(second) and first == second
    try:
        a, b = Decimal(str(first)), Decimal(str(second))
        if a.is_finite() and b.is_finite():
            return a == b
    except (ValueError, InvalidOperation):
        pass
    return type(first) is type(second) and first == second


def _coherence(cohort, row, history):
    scope, target = history['scope'], history['target']
    if scope.get('temporal_scope') != TEMPORAL_SCOPE or scope.get('stage', 'ADJUDICACION') != 'ADJUDICACION':
        return 'alcance_o_etapa_incompatible'
    if scope.get('snapshot_cut') != cohort['scope']['snapshot_cut']:
        return 'corte_incompatible'
    if (type(row.get('fuente_id')) is not int or row['fuente_id'] < 1
            or type(row.get('unit_rows_up_to_two')) is not int or row['unit_rows_up_to_two'] != 1
            or not all(official_id(row.get(key)) for key in ('socrata_row_id', 'id_del_proceso', 'id_adjudicacion'))):
        return 'identidad_cohorte_no_admisible'
    if str(row.get('adjudicado') or '').strip().upper() not in {'SI', 'SÍ', 'TRUE', '1'}:
        return 'adjudicacion_cohorte_no_confirmada'
    if (type(target.get('source_id')) is not int or target['source_id'] != row['fuente_id']
            or official_id(target.get('process_id')) != official_id(row['id_del_proceso'])
            or official_id(target.get('award_id')) != official_id(row['id_adjudicacion'])):
        return 'identidad_operacion_incompatible'
    if target.get('identity_verified') is not True:
        return 'identidad_historia_no_admisible'
    if official_id(target.get('category')) != official_id(row.get('codigo_principal_de_categoria')):
        return 'categoria_objetivo_incompatible'
    if _method(target.get('method')) != _method(row.get('modalidad_contratacion')):
        return 'modalidad_objetivo_incompatible'
    if not _same_amount(target.get('amount'), row.get('valor_total_adjudicacion')):
        return 'importe_objetivo_incompatible'
    try:
        at = instant(target['award_at'])
        # Cut dates are inclusive Bogotá civil dates (UTC-5 for this SECOP cut).
        cut_end = datetime.combine(date.fromisoformat(scope['snapshot_cut']) + timedelta(days=1),
                                   time(), tzinfo=timezone(timedelta(hours=-5)))
        if at >= cut_end:
            return 'adjudicacion_posterior_al_corte'
        if at.astimezone(timezone(timedelta(hours=-5))).date() < date.fromisoformat(row['fecha_publicacion_normalizada']):
            return 'adjudicacion_anterior_a_publicacion'
    except (ValueError, TypeError, KeyError, AttributeError):
        return 'fecha_objetivo_no_admisible'
    return None


def assess(cohort, histories):
    """Histories may be streamed. Missing/incompatible history cannot erase IQR."""
    iqr = assess_iqr(cohort)
    raw = {row['id']: row for row in cohort['rows']}
    units = Counter((row.get('fuente_id'), official_id(row.get('id_del_proceso')),
                     official_id(row.get('id_adjudicacion'))) for row in cohort['rows'])
    targets = {row['contract_id'] for row in iqr['results']}
    accepted, failures, provenance, seen = {}, {}, {}, set()
    for index, history in enumerate(histories):
        if index >= 1000:
            raise ValueError('Máximo de 1000 historias por composición')
        key = history.get('scope', {}).get('local_contract_id')
        if type(key) is not int or key not in targets or key in seen:
            raise ValueError('Historia sin objetivo seleccionado único de la cohorte')
        seen.add(key)
        provenance[key] = digest(history)
        try:
            row = raw[key]
            reason = ('unidad_repetida_en_cohorte' if units[(row.get('fuente_id'), official_id(row.get('id_del_proceso')),
                                                          official_id(row.get('id_adjudicacion')))] > 1
                      else _coherence(cohort, row, history))
            if reason is None:
                computed = assess_rolling(history)
                # Keep compact evidence summaries, not every award in every
                # streamed history. The original hashed inputs remain the trace.
                accepted[key] = {name: computed[name] for name in ('values', 'target', 'frame')}
                accepted[key]['indicators'] = {name: {'reasons': item['reasons']}
                                                for name, item in computed['indicators'].items()}
                del computed
        except (ValueError, TypeError, KeyError, AttributeError):
            reason = 'historia_no_admisible'
        if reason:
            failures[key] = reason
    results, reason_counts = [], Counter()
    for original in iqr['results']:
        key = original['contract_id']
        rolling = accepted.get(key)
        reason = failures.get(key, 'sin_historia_comprobada' if rolling is None else None)
        finding = original['coverage']['indicators']['IMPORTE_ATIPICO']['observed']
        values = {'modalidad': raw[key]['modalidad_contratacion']}
        if rolling is not None:
            values.update(rolling['values'])
        coverage = baseline_coverage(values, 'ADJUDICACION', finding)
        for indicator, field in (('DIRECTAS_90D', 'directas_90d'), ('REITERACION_30D', 'reiteraciones_30d')):
            if rolling is None:
                coverage['indicators'][indicator]['reason'] = reason
            else:
                coverage['indicators'][indicator]['context_quality_reasons'] = rolling['indicators'][field]['reasons']
        if reason: reason_counts[reason] += 1
        results.append({key: value for key, value in original.items() if key != 'coverage'} | {
            'composition_policy': POLICY, 'coverage': coverage,
            'snapshot_cut': cohort['scope']['snapshot_cut'], 'history_accepted': rolling is not None,
            'history_abstention_reason': reason, 'history_canonical_sha256': provenance.get(key),
            'rolling_anchor_at': rolling['target']['award_at'] if rolling else None,
            'rolling_universe': rolling['frame']['universe'] if rolling else None,
            'database_generation_consistency_verified': False,
            'source_currency_verified': False, 'model_index': None,
            'publication_authorized': False})
    families = ('IMPORTE_ATIPICO', 'COMPETENCIA', 'CONCENTRACION_REITERACION')
    report = {'policy': POLICY, 'temporal_scope': TEMPORAL_SCOPE, 'snapshot_cut': cohort['scope']['snapshot_cut'],
            'scope': 'descriptive_same_declared_cut_with_shared_target_fact_checks',
            'cohort_canonical_sha256': digest(cohort), 'iqr_reference': iqr['reference'],
            'reference_family_weights': {name: 1 for name in families}, 'results': results,
            'targets': len(results), 'histories_supplied': len(seen), 'histories_accepted': len(accepted),
            'history_abstention_counts': dict(reason_counts),
            'family_status_counts': {name: dict(Counter(row['coverage']['families'][name]['status'] for row in results)) for name in families},
            'complete_descriptive_counts': sum(row['coverage']['complete_score'] is not None for row in results),
            'database_generation_consistency_verified': False, 'training_eligible': False,
            'model_index': None, 'publication_authorized': False,
            'limitations': ['Fechas de corte y hechos del objetivo coincidentes no acreditan una generación común de base de datos.',
                            'IQR utiliza el grupo completo del corte; ventanas se anclan en adjudicación con información del corte actual.',
                            'No reconstruye disponibilidad histórica, no admite entrenamiento ni estima probabilidad de corrupción.',
                            'Competencia permanece sin evaluar salvo no aplicabilidad explícita de la referencia.',
                            'No utiliza puntajes de proveedor ni denomina bajo riesgo a resultados incompletos.']}
    priority = assess_priority(report)
    report['priority_analysis'] = {key:value for key,value in priority.items() if key != 'results'}
    report['priority_analysis']['input_hash_scope'] = 'joint_baseline_before_priority_augmentation'
    for row, assessment in zip(results, priority['results']):
        row['priority'] = {key:value for key,value in assessment.items() if key != 'contract_id'}
    return report
