from pydantic import BaseModel, Field
from modules.transformacion.domain.filters import ContratoProcesadoFilter, AnomaliaFilter


class ContratoProcesadoFilterDTO(ContratoProcesadoFilter):
    """HTTP representation of contract search filters."""


class AnomaliaFilterDTO(AnomaliaFilter):
    """HTTP representation of anomaly search filters."""


class ReprocesarRequestDTO(BaseModel):
    """Parámetros para el endpoint de reprocesamiento"""
    forzar_reproceso: bool = Field(
        False,
        description=(
            "false (default): procesa registros nuevos o sincronizados después de su último procesamiento. "
            "true: ignora si el registro ya fue procesado y lo evalúa de nuevo, "
            "útil cuando cambia la lógica de normalización."
        )
    )
