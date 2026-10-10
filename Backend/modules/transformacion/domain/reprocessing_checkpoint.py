"""Validation of durable transformation progress, without database dependencies."""
from datetime import date, datetime


def validate_checkpoint(universe: dict, *, job_id: int, rule_version: str,
                        stored_rule_version: str, counters: dict) -> bool:
    """Legacy logs are not resumable; invalid versioned progress must not be skipped."""
    if "version_checkpoint" not in universe:
        return False
    if (type(universe["version_checkpoint"]) is not int or universe["version_checkpoint"] != 1
            or stored_rule_version != rule_version
            or type(universe.get("background_job_id")) is not int
            or universe.get("background_job_id") != job_id
            or universe.get("forzar_reproceso") is not True):
        raise ValueError("El avance guardado no corresponde a este reprocesamiento")
    keys = ("max_raw_secop_id", "ultimo_raw_secop_id", "total_candidatos", "total_evaluados")
    values = [universe.get(key) for key in keys] + list(counters.values())
    if any(type(value) is not int or value < 0 for value in values):
        raise ValueError("El avance guardado contiene contadores inválidos")
    maximum, cursor, candidates, evaluated = (universe[key] for key in keys)
    if (cursor > maximum or evaluated > candidates or evaluated > cursor
            or (evaluated == 0 and cursor != 0)
            or candidates > maximum or counters["total_evaluados"] != evaluated
            or counters["procesados"] + counters["omitidos"] != evaluated):
        raise ValueError("El avance guardado contiene un alcance inconsistente")
    try:
        date.fromisoformat(universe["fecha_referencia_anomalias"])
        datetime.fromisoformat(universe["candidatos_verificados_en"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("El avance guardado no tiene una referencia temporal válida") from exc
    return True
