"""Anomaly finding independent of HTTP and database models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnomalyFinding:
    raw_secop_id: int
    motivo: str
    valor_detectado: str | None
    tipo_anomalia: str
    valor_original: str | None
    descripcion: str
    campo_afectado: str
