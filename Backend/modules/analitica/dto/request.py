from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class OutlierCalculoRequest(BaseModel):
    """
    Parámetros para disparar una nueva ejecución del análisis IQR.
    Todos los campos son opcionales; sin filtros se analiza el universo completo.
    """
    campo_analizado: str = Field(
        default="valor_total_normalizado",
        description="Campo numérico de contratos_procesados a analizar.",
        pattern="^(valor_total_normalizado|precio_base_normalizado)$"
    )
    fecha_desde: Optional[date] = Field(
        default=None,
        description="Filtro por fecha_publicacion_normalizada (inclusive)."
    )
    fecha_hasta: Optional[date] = Field(
        default=None,
        description="Filtro por fecha_publicacion_normalizada (inclusive)."
    )
    modalidades: Optional[list[str]] = Field(
        default=None,
        description="Lista de modalidades_de_contratacion a incluir. Null = todas."
    )


class OutlierFiltroRequest(BaseModel):
    """
    Parámetros de consulta para listar outliers ya calculados.
    """
    run_id: Optional[str] = Field(
        default=None,
        description="Filtrar por ejecución específica. Null = última ejecución."
    )
    solo_outliers: bool = Field(
        default=False,
        description="True = retorna solo contratos marcados como outlier."
    )
    grupo: Optional[str] = Field(
        default=None,
        description="Filtrar por modalidad o tipo de contrato."
    )
    direccion: Optional[str] = Field(
        default=None,
        description="'ALTO' | 'BAJO'. Null = ambos.",
        pattern="^(ALTO|BAJO)$"
    )
    score_minimo: Optional[float] = Field(
        default=None,
        ge=0,
        description="Retorna solo outliers con score >= este valor."
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)