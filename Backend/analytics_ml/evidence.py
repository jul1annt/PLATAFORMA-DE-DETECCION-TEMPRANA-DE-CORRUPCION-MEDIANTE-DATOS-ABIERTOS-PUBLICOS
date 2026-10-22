"""Verify preserved feature sources against a separately reviewed registry.

Hashes establish byte integrity, not the truth of a judicial or procurement
document. An authenticated reviewer must check dates, locators, values and the
operation/stage before registering a historical snapshot. Dataset declarations
alone never make a snapshot eligible for training.
"""
from collections import Counter
from pathlib import Path
import hashlib
import math
import re
from decimal import Decimal, InvalidOperation
from modules.motor_riesgo.domain import digest, instant, features, identity_reasons, public_document, stage_time_reasons

POLICY = 'reviewed-physical-stage-evidence-v2'
MONETARY_MEASURES = {'log_presupuesto': 'PRESUPUESTO_PROCESO', 'log_adjudicado': 'VALOR_ADJUDICADO'}


def validate_monetary_field(name: str, field: dict, assertion: dict, review: dict) -> None:
    """Admit one explicit monetary scale, without inventing conversions.

    Historical concessions may report VPIT in constant pesos. A numeric match
    with a current SECOP amount cannot silently turn that quantity into a
    nominal award. Missing/unsupported monetary evidence stays outside the
    reviewed registry; other indicators can still use separately valid fields.
    """
    if name not in MONETARY_MEASURES or field.get('value') is None:
        return
    monetary = field.get('monetary')
    if (not isinstance(monetary, dict) or review.get('monetary_basis_verified') is not True
            or monetary.get('currency') != 'COP' or monetary.get('unit') != 'PESOS'
            or monetary.get('price_basis') != 'NOMINAL'
            or monetary.get('measure') != MONETARY_MEASURES[name]
            or monetary.get('transform') != 'LOG1P'
            or assertion.get('monetary_sha256') != digest(monetary)
            or not isinstance(assertion.get('monetary_locator'), str)
            or not assertion['monetary_locator'].strip()):
        raise ValueError('Base monetaria no verificada o incompatible: ' + name)
    raw = monetary.get('raw_amount')
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError('El importe original requiere una representación decimal explícita')
    try:
        amount = Decimal(raw)
        number = float(amount)
        supplied = field.get('value')
        if (not amount.is_finite() or amount <= 0 or not math.isfinite(number)
                or type(supplied) not in (float, int) or not math.isfinite(supplied)
                or not math.isclose(float(supplied), math.log1p(number), rel_tol=1e-12, abs_tol=0.0)):
            raise ValueError('Importe original o transformación monetaria incoherente: ' + name)
    except (InvalidOperation, OverflowError) as exc:
        raise ValueError('Importe original inválido: ' + name) from exc


def validate_record(record: dict, root: Path) -> None:
    if not isinstance(record.get('evidence_id'), str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', record['evidence_id']):
        raise ValueError('Identificador de evidencia inválido')
    review = record.get('review', {})
    if any(review.get(name) is not True for name in ('dates_verified', 'values_verified', 'identity_verified', 'stage_verified')):
        raise ValueError('Se requiere revisión explícita de fecha, valor, identidad y etapa')
    observation = record['observation']
    stage = observation['stage']
    if identity_reasons(observation, stage) or observation.get('feature_evidence_id') is not None:
        raise ValueError('La observación revisada debe identificar una operación y etapa sin ambigüedad')
    if stage_time_reasons(observation):
        raise ValueError('El entrenamiento requiere reconstruir el momento de la etapa')
    features(observation, stage)
    at = instant(observation['prediction_at'])
    documents = {}
    root = root.resolve()
    for document in record.get('documents', []):
        key = document['document_id']
        if not isinstance(key, str) or not key or key in documents:
            raise ValueError('Documento sin identidad o duplicado')
        path = (root / document['file']).resolve()
        if not path.is_relative_to(root) or not path.is_file() or not 0 < path.stat().st_size <= 64 * 1024**2:
            raise ValueError('Documento local ausente, fuera del directorio o mayor de 64 MiB')
        if not public_document(document['url']):
            raise ValueError('La evidencia requiere una fuente oficial HTTPS')
        with path.open('rb') as source:
            if hashlib.file_digest(source, 'sha256').hexdigest() != document['sha256']:
                raise ValueError('Documento físico distinto del revisado')
        available = instant(document['available_at'])
        if available > at:
            raise ValueError('Documento conocido después de la predicción')
        basis = document['temporal_basis']
        if basis == 'CAPTURE_LOG':
            if instant(document['captured_at']) > available:
                raise ValueError('La captura observada no puede retrofecharse')
        elif basis != 'ORIGINAL_DATED_DOCUMENT':
            raise ValueError('Procedencia temporal sin verificar')
        documents[key] = document
    assertions = record.get('field_evidence', {})
    if not observation.get('fields') or set(assertions) != set(observation['fields']):
        raise ValueError('Cada campo requiere evidencia documental revisada')
    for name, field in observation['fields'].items():
        assertion = assertions[name]
        validate_monetary_field(name, field, assertion, review)
        ids = assertion.get('document_ids', [])
        if (not ids or len(ids) != len(set(ids)) or any(key not in documents for key in ids)
                or not isinstance(assertion.get('locator'), str) or not assertion['locator'].strip()):
            raise ValueError('Localizador o referencia de campo inválidos')
        if assertion.get('value_sha256') != digest(field.get('value')):
            raise ValueError('Valor distinto de la extracción revisada')
        if field.get('sha256') != digest({key: documents[key]['sha256'] for key in ids}):
            raise ValueError('El hash del campo no corresponde a sus documentos físicos')
        if any(instant(documents[key]['available_at']) > instant(field['available_at']) for key in ids):
            raise ValueError('El campo precede a su evidencia')


def verified_observations(observations: list[dict], records: list[dict], root: Path):
    registry, invalid = {}, set()
    for entry in records:
        record = entry.get('record', {})
        key = record.get('evidence_id')
        if key in registry or key in invalid:
            raise ValueError('Evidencia de variables duplicada')
        try:
            if (type(entry.get('registered_by')) is not int or entry['registered_by'] < 1
                    or entry.get('record_sha256') != digest(record)):
                raise ValueError('Registro no aprobado por administración')
            validate_record(record, root)
            registry[key] = record
        except (KeyError, ValueError, TypeError, OSError, OverflowError):
            invalid.add(key)
    accepted, exclusions = [], Counter()
    for observation in observations:
        key = observation.get('feature_evidence_id')
        if key not in registry:
            exclusions['evidencia_fisica_no_verificada' if key in invalid else 'sin_registro_de_evidencia_revisada'] += 1
            continue
        actual = {k: v for k, v in observation.items() if k != 'feature_evidence_id'}
        if digest(actual) != digest(registry[key]['observation']):
            exclusions['observacion_distinta_de_revision'] += 1
            continue
        accepted.append(observation)
    summary = {'policy': POLICY, 'registry_sha256': digest(records), 'input_rows': len(observations),
               'verified_rows': len(accepted), 'excluded': dict(exclusions), 'verified_registry_records': len(registry),
               'scope': 'physical_integrity_and_authenticated_human_review; not_automated_verification_of_document_truth'}
    return accepted, summary
