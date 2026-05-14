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

class DuplicadoCalculoRequest(BaseModel):
    """
    Parámetros para disparar una nueva ejecución del análisis de duplicados en período corto.
    Todos los campos son opcionales; sin filtros se analiza el universo completo.
    """
    fecha_desde: Optional[date] = Field(
        default=None,
        description="Filtro por fecha_publicacion_normalizada (inclusive)."
    )
    fecha_hasta: Optional[date] = Field(
        default=None,
        description="Filtro por fecha_publicacion_normalizada (inclusive)."
    )

class DuplicadoFiltroRequest(BaseModel):
    """
    Parámetros de consulta para listar duplicados ya calculados.
    """
    run_id: Optional[str] = Field(
        default=None,
        description="Filtrar por ejecución específica. Null = última ejecución."
    )
    riesgo: Optional[str] = Field(
        default=None,
        description="'ALTO' | 'MEDIO' | 'BAJO'. Null = todos.",
        pattern="^(ALTO|MEDIO|BAJO)$"
    )
    score_minimo: Optional[float] = Field(
        default=None,
        ge=0,
        description="Retorna solo duplicados con score >= este valor."
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class AdjudicacionDirectaCalculoRequest(BaseModel):
    """
    Parámetros para disparar una nueva ejecución del análisis de abuso
    de adjudicación directa por proveedor.
    """
    fecha_desde: Optional[date] = Field(
        default=None,
        description="Filtro por fecha_publicacion_normalizada (inclusive)."
    )
    fecha_hasta: Optional[date] = Field(
        default=None,
        description="Filtro por fecha_publicacion_normalizada (inclusive)."
    )
    minimo_directas: int = Field(
        default=3,
        ge=1,
        description="Umbral mínimo de contratos directos para considerar abuso."
    )
    dias_ventana: int = Field(
        default=90,
        ge=1,
        description="Ventana de días para analizar la concentración de directas."
    )


class AdjudicacionDirectaFiltroRequest(BaseModel):
    """
    Parámetros de consulta para listar proveedores con abuso de adjudicación directa.
    """
    run_id: Optional[str] = Field(
        default=None,
        description="Filtrar por ejecución específica. Null = última ejecución."
    )
    riesgo: Optional[str] = Field(
        default=None,
        description="'ALTO' | 'MEDIO' | 'BAJO'. Null = todos.",
        pattern="^(ALTO|MEDIO|BAJO)$"
    )
    score_minimo: Optional[float] = Field(
        default=None,
        ge=0,
        description="Retorna solo proveedores con score >= este valor."
    )
    score_maximo: Optional[float] = Field(
        default=None,
        ge=0,
        description="Retorna solo proveedores con score <= este valor."
    )
    porcentaje_minimo: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Retorna solo proveedores con porcentaje_directos >= este valor."
    )
    porcentaje_maximo: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Retorna solo proveedores con porcentaje_directos <= este valor."
    )
    solo_abuso_directas: bool = Field(
        default=False,
        description="True = retorna solo proveedores con clasificacion ALTO o MEDIO."
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
