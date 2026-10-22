"""Pure, dependency-free contracts shared by training and batch inference."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import re
import ast
from urllib.parse import urlsplit

STAGES = ("CONVOCATORIA", "ADJUDICACION")
FEATURE_VERSION = "secop-point-in-time-v3"
PREDICTION_POLICY = "reviewed-stage-landmark-v1"
NUMERIC = {
    "CONVOCATORIA": ("log_presupuesto", "plazo_dias", "duracion_dias", "procesos_previos", "concentracion_previa"),
    "ADJUDICACION": ("log_presupuesto", "plazo_dias", "duracion_dias", "procesos_previos", "concentracion_previa", "log_adjudicado", "oferentes", "reiteraciones_30d", "directas_90d"),
}
CATEGORICAL = ("categoria", "modalidad", "departamento")
REFERENCES = {
    "ocp": "https://www.open-contracting.org/resources/red-flags-in-public-procurement-a-guide-to-using-data-to-detect-and-mitigate-risks/",
    "cri": "https://doi.org/10.1007/s10610-016-9308-z",
    "colombia": "https://imco.org.mx/wp-content/uploads/2019/07/FEDESARROLLO_CPBD.pdf",
    "pu": "https://arxiv.org/abs/2102.05523",
}


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("La fecha debe incluir zona horaria")
    return parsed.astimezone(timezone.utc)


def public_document(url: str) -> bool:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and not parsed.username and not parsed.password and (
        host.endswith(".gov.co") or host.endswith(".ramajudicial.gov.co"))


def official_id(value) -> str | None:
    """Preserve official spelling, but never treat missing-value tokens as IDs."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value.upper() not in {'', 'N/A', 'NA', 'NULL', 'NONE', 'NO DEFINIDO', 'NO ADJUDICADO', 'SIN DATO', 'NO APLICA'} else None


def secop_source_url(value) -> str | None:
    if isinstance(value, str) and len(value) <= 4096 and value.strip().startswith('{'):
        try:
            value = ast.literal_eval(value.strip())
        except (ValueError, SyntaxError, RecursionError):
            try:
                value = json.loads(value.strip())
            except (ValueError, RecursionError):
                return None
    if isinstance(value, dict):
        value = value.get('url')
    if not isinstance(value, str) or len(value) > 4096 or '\\' in value or any(ord(c) < 32 for c in value):
        return None
    value = value.strip()
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or '').lower()
        official = any(host == domain or host.endswith('.' + domain) for domain in ('secop.gov.co', 'contratos.gov.co'))
        if parsed.scheme == 'https' and official and not parsed.username and not parsed.password and parsed.port in {None, 443}:
            return value
    except ValueError:
        pass
    return None


def operation_key(observation: dict, stage: str) -> tuple:
    """A source row is traceability; it is not an independent procurement unit."""
    return (observation.get('source_id'), official_id(observation.get('process_id')),
            official_id(observation.get('lot_id')),
            official_id(observation.get('award_id')) if stage == 'ADJUDICACION' else None)


def identity_reasons(observation: dict, stage: str) -> list[str]:
    reasons = []
    if (observation.get('stage') != stage or type(observation.get('source_id')) is not int
            or observation['source_id'] < 1 or not official_id(observation.get('source_row_id'))
            or not official_id(observation.get('process_id'))):
        reasons.append('identidad_o_etapa_incompleta')
    if stage == 'ADJUDICACION' and not official_id(observation.get('award_id')):
        reasons.append('identidad_adjudicacion_incompleta')
    if observation.get('identity_ambiguous'):
        reasons.append('identidad_operacion_ambigua')
    return reasons


def stage_time_reasons(observation: dict) -> list[str]:
    """Current captures cannot stand in for information known at a past stage."""
    if observation.get('temporal_scope') != 'historical_stage_snapshot':
        return ['sin_reconstruccion_temporal_de_etapa']
    try:
        if instant(observation['stage_event_at']) != instant(observation['prediction_at']):
            return ['momento_de_prediccion_distinto_de_etapa']
    except (KeyError, TypeError, ValueError, AttributeError):
        return ['fecha_etapa_no_verificable']
    return []


def eligible_case(case: dict) -> list[str]:
    """No supplier-wide propagation; source facts must identify an exact operation."""
    reasons = []
    if case.get('registration_eligible') is False:
        reasons.append('registro_de_base_no_elegible')
    for field in ("case_id", "authority", "docket", "conduct", "published_at", "final_at", "verified_by"):
        if not case.get(field):
            reasons.append("falta_" + field)
    if not case.get('first_investigation_at'):
        reasons.append('falta_corte_temporal_preinvestigacion')
    else:
        try:
            if case.get('published_at') and instant(case['first_investigation_at']) > instant(case['published_at']):
                reasons.append('investigacion_posterior_a_etiqueta')
        except (ValueError, TypeError):
            reasons.append('fechas_invalidas')
    if case.get("conduct") not in {"CORRUPCION", "FRAUDE_CONTRACTUAL"}:
        reasons.append("conducta_fuera_del_objetivo")
    for field in ("judgment", "finality"):
        evidence = case.get(field) or {}
        if not public_document(evidence.get("url", "")) or not re.fullmatch(r'[a-f0-9]{64}', evidence.get("sha256", "")):
            reasons.append("evidencia_" + field + "_incompleta")
    if case.get("status") != "VERIFICADO":
        reasons.append("decision_no_verificada")
    operations = case.get("operations") or []
    if not operations or any(not x.get("source_row_id") or not x.get("process_id") or x.get("match") != "EXACTO" for x in operations):
        reasons.append("vinculo_secop_no_exacto")
    for operation in operations:
        stages = operation.get('stages', ['ADJUDICACION'] if operation.get('award_id') else ['CONVOCATORIA'])
        if not isinstance(stages, list) or not stages or any(s not in STAGES for s in stages):
            reasons.append('etapas_del_vinculo_invalidas')
        elif any(identity_reasons({**operation, 'stage': stage}, stage) for stage in stages):
            reasons.append('identidad_del_vinculo_incompleta')
    if case.get("published_at") and case.get("final_at"):
        try:
            if instant(case["final_at"]) > instant(case["published_at"]):
                reasons.append("firmeza_posterior_a_disponibilidad_etiqueta")
        except (ValueError, TypeError):
            reasons.append("fechas_invalidas")
    return sorted(set(reasons))


def features(observation: dict, stage: str) -> tuple[dict, list[str]]:
    """Only explicitly evidenced, available-at fields reach the estimator.

    A current SECOP row is NOT evidence of its state at publication/award time.
    Each supplied field carries its original value and an evidence timestamp/hash.
    """
    if stage not in STAGES:
        raise ValueError("Etapa inválida")
    at = instant(observation["prediction_at"])
    reasons = identity_reasons(observation, stage)
    values = {}
    fields = observation.get("fields", {})
    for name in (*NUMERIC[stage], *CATEGORICAL):
        field = fields.get(name)
        if not isinstance(field, dict) or not re.fullmatch(r'[a-f0-9]{64}', field.get('sha256', '')):
            reasons.append("sin_evidencia:" + name)
            values[name] = None
            continue
        if instant(field["available_at"]) > at or (field.get("event_at") and instant(field["event_at"]) > at):
            raise ValueError("Información futura: " + name)
        value = field.get("value")
        if name in NUMERIC[stage] and value is not None:
            value = float(value)
            if not math.isfinite(value) or value < 0:
                raise ValueError("Variable numérica inválida: " + name)
        elif value is not None:
            value = str(value).strip().upper()[:200] or None
        values[name] = value
    return values, sorted(set(reasons))


def percentile(reference: list[float], score: float) -> float:
    from bisect import bisect_left, bisect_right
    if not reference or not math.isfinite(score):
        raise ValueError("Referencia de índice inválida")
    # Midrank makes ties deterministic instead of ranking them by database ID.
    return round(100 * (bisect_left(reference, score) + bisect_right(reference, score)) / (2 * len(reference)), 2)
