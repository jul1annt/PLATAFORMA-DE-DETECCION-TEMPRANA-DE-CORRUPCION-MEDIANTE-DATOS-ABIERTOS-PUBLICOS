"""Evidence-backed inventory. This module never invents judicial labels."""
from pathlib import Path
import hashlib
from collections import Counter
import re
import unicodedata
from modules.motor_riesgo.domain import eligible_case, features, digest, instant, operation_key, identity_reasons, stage_time_reasons

JUDICIAL_REVIEW_POLICY = 'reviewed-finality-effect-v2'
FINALITY_KINDS = frozenset({'CONSTANCIA_EJECUTORIA', 'PROVIDENCIA_ULTIMO_RECURSO',
                            'PROVIDENCIA_ACREDITA_FIRMEZA'})


def case_groups(cases: dict) -> dict:
    """Join declared relations, shared decisions and repeated official dockets.

    Separate registry IDs cannot manufacture independent judicial proceedings.
    This grouping is used only for sample separation, never as a predictor.
    """
    parents = {key: key for key in cases}
    def root(key):
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key
    def normalized(value):
        value = ''.join(c for c in unicodedata.normalize('NFKD', str(value or '').upper()) if not unicodedata.combining(c))
        return re.sub(r'[^A-Z0-9]', '', value)
    seen = {}
    for key in sorted(cases):
        case = cases[key]
        tokens = []
        if case.get('related_group'):
            tokens.append(('declared', case['related_group']))
        if case.get('docket') and case.get('authority'):
            tokens.append(('docket', normalized(case['authority']), normalized(case['docket'])))
        if (case.get('judgment') or {}).get('sha256'):
            tokens.append(('decision', case['judgment']['sha256']))
        for token in tokens:
            if token in seen:
                first, second = root(key), root(seen[token])
                parents[max(first, second)] = min(first, second)
            else:
                seen[token] = key
    return {key: root(key) for key in cases}


def verified_cases(cases: list[dict], evidence_root: Path) -> tuple[dict, dict]:
    accepted, exclusions = {}, []
    root = evidence_root.resolve()
    for case in cases:
        reasons = eligible_case(case)
        judgment=case.get('judgment') or {}
        finality=case.get('finality') or {}
        if judgment.get('kind')!='SENTENCIA_CONDENATORIA':
            reasons.append('falta_sentencia_condenatoria_identificada')
        if (finality.get('kind') not in FINALITY_KINDS
                or not judgment.get('sha256') or finality.get('judgment_sha256')!=judgment['sha256']):
            reasons.append('firmeza_no_vinculada_a_sentencia_condenatoria')
        # Some official documents headed "constancia de ejecutoria" merely
        # OPEN the appeal period. A scheduled expiry, or an unappealable order
        # announcing a future verdict, is not proof that the conviction is final.
        # The physical document and its legal effect require an explicit review;
        # never infer finality by counting elapsed days or by matching a title.
        if (finality.get('reviewed') is not True
                or finality.get('effect')!='FIRMEZA_CONFIRMADA'
                or not isinstance(finality.get('locator'),str) or not finality['locator'].strip()):
            reasons.append('firmeza_sin_efecto_confirmado_y_revisado')
        if finality.get('kind') == 'PROVIDENCIA_ACREDITA_FIRMEZA':
            # A later judicial decision can explicitly certify the earlier
            # conviction's finality without being the last appeal itself. Its
            # own date is not the finality date: require the declaration and its
            # locator, in addition to the original file/hash and effect review.
            try:
                if instant(finality['declared_final_at']) != instant(case['final_at']):
                    reasons.append('fecha_firmeza_declarada_no_coincide')
            except (KeyError, ValueError, TypeError, AttributeError):
                reasons.append('fecha_firmeza_declarada_ausente_o_invalida')
            if (not isinstance(finality.get('declaration_date_locator'), str)
                    or not finality['declaration_date_locator'].strip()):
                reasons.append('fecha_firmeza_sin_localizador_declaracion')
        if case.get('conduct') == 'FRAUDE_CONTRACTUAL':
            reasons.append('fraude_contractual_separado_del_objetivo_corrupcion')
        for operation in case.get('operations') or []:
            # A conviction can coexist with acquittals or partial nullities in
            # the same file. Exact SECOP identity alone does not prove that the
            # operation belongs to the facts actually covered by the conviction.
            link=operation.get('judicial_link')
            if (not isinstance(link,dict) or link.get('reviewed') is not True
                    or link.get('outcome')!='CONDENA_CORRUPCION'
                    or link.get('judgment_sha256')!=judgment.get('sha256')
                    or any(not isinstance(link.get(name),str) or not link[name].strip()
                           for name in ('facts_locator','operative_locator'))):
                reasons.append('operacion_sin_condena_por_corrupcion_documentada')
        for field in ('judgment', 'finality'):
            evidence = case.get(field) or {}
            path = (root / evidence.get('file', '__missing__')).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                reasons.append('documento_local_ausente:' + field)
            else:
                with path.open('rb') as source:
                    if hashlib.file_digest(source, 'sha256').hexdigest() != evidence.get('sha256'):
                        reasons.append('hash_documental_distinto:' + field)
        key = case.get('case_id')
        if key in accepted:
            raise ValueError('Expediente duplicado')
        if reasons:
            exclusions.append({'case_id': key, 'reasons': sorted(set(reasons))})
        else:
            accepted[key] = case
    return accepted, {'candidates': len(cases), 'eligible_cases': len(accepted), 'exclusions': exclusions,
                      'judicial_review_policy': JUDICIAL_REVIEW_POLICY,
                      'training_target': 'CORRUPCION', 'registry_by_conduct': dict(Counter(c.get('conduct', 'SIN_CLASIFICAR') for c in cases)),
                      'independent_case_groups': len(set(case_groups(accepted).values())),
                      'temporal_coverage': sorted(c['published_at'] for c in accepted.values()),
                      'case_registry_sha256': digest(cases), 'judicial_identity_inferred': False}


def prepare_rows(observations: list[dict], cases: dict, stage: str) -> tuple[list[dict], dict]:
    groups = case_groups(cases)
    links = {}
    for case in cases.values():
        if case['conduct'] != 'CORRUPCION':
            continue
        for op in case['operations']:
            # Projection from an award to its call requires an explicit reviewed
            # stage link. Never label every call of a convicted supplier.
            stages = op.get('stages', ['ADJUDICACION'] if op.get('award_id') else ['CONVOCATORIA'])
            if stage not in stages:
                continue
            key = (op['source_id'], op['source_row_id'], operation_key(op, stage))
            if key in links and links[key]['case_id'] != case['case_id']:
                raise ValueError('Una operación pertenece a varios expedientes; agrupar y resolver explícitamente')
            links[key] = case
    rows, excluded, seen = [], Counter(), set()
    unit_counts = Counter(operation_key(o, stage) for o in observations if o.get('stage') == stage)
    for observation in observations:
        if observation.get('stage') != stage:
            continue
        if observation.get('snapshot') is not None and observation.get('snapshot_sha256') != digest(observation['snapshot']):
            excluded['snapshot_alterado'] += 1
            continue
        key = (observation.get('source_id'), observation.get('source_row_id'), operation_key(observation, stage))
        if key in seen:
            raise ValueError('Operación/etapa duplicada en el conjunto')
        seen.add(key)
        identity = identity_reasons(observation, stage)
        if identity:
            excluded.update(identity)
            continue
        temporal = stage_time_reasons(observation)
        if temporal:
            excluded.update(temporal)
            continue
        if unit_counts[operation_key(observation, stage)] > 1:
            excluded['identidad_operacion_ambigua'] += 1
            continue
        try:
            values, reasons = features(observation, stage)
        except (ValueError, KeyError, TypeError):
            excluded['evidencia_temporal_invalida'] += 1
            continue
        essential = ('log_presupuesto', 'categoria', 'modalidad') + (('log_adjudicado',) if stage == 'ADJUDICACION' else ())
        if any(values[n] is None for n in essential):
            excluded['variables_esenciales_ausentes'] += 1
            continue
        case = links.get(key)
        if case and not case.get('first_investigation_at'):
            excluded['falta_corte_temporal_preinvestigacion'] += 1
            continue
        if case and instant(observation['prediction_at']) >= instant(case['first_investigation_at']):
            excluded['observacion_posterior_a_investigacion'] += 1
            continue
        # Preserve unknown supplier groups; never equate an absent NIT with one supplier.
        normalized = instant(observation['prediction_at']).isoformat()
        rows.append({**observation, 'prediction_at': normalized, 'values': values, 'positive': bool(case), 'reasons': reasons,
                     'case_conduct': case['conduct'] if case else None,
                     'case_group': groups[case['case_id']] if case else None,
                     'label_available_at': instant(case['published_at']).isoformat() if case else None})
    return rows, {'stage': stage, 'usable_rows': len(rows), 'known_positive_rows': sum(r['positive'] for r in rows),
                  'independent_positive_cases': len({r['case_group'] for r in rows if r['positive']}), 'excluded': dict(excluded)}
