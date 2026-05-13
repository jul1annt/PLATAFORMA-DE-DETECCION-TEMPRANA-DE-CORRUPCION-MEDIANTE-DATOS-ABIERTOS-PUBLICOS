from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class EstadisticasGrupoResponse(BaseModel):
    """Resumen estadístico de un grupo (modalidad o tipo de contrato)."""
    grupo: str
    q1: float
    q3: float
    iqr: float
    limite_inferior: float
    limite_superior: float
    total_contratos_analizados: int
    total_outliers: int
    total_outliers_alto: int
    total_outliers_bajo: int

    class Config:
        from_attributes = True


class OutlierDetalleResponse(BaseModel):
    """Un contrato con su clasificación outlier y score."""
    id: UUID
    contrato_id: int
    run_id: UUID
    grupo: str
    campo_analizado: str
    valor: float
    q1: float
    q3: float
    iqr: float
    limite_inferior: float
    limite_superior: float
    es_outlier: bool
    direccion_outlier: Optional[str]

    # Score: cuántas veces el IQR sobrepasa el límite correspondiente.
    # Ej: score=2.5 significa que el valor está 2.5 IQRs por encima del límite superior.
    score: float

    fecha_calculo: datetime

    class Config:
        from_attributes = True


class OutlierListaResponse(BaseModel):
    """Respuesta paginada del listado de outliers."""
    items: list[OutlierDetalleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RunResumenResponse(BaseModel):
    """Resumen de una ejecución completa del análisis."""
    run_id: UUID
    campo_analizado: str
    total_contratos_analizados: int
    total_outliers: int
    porcentaje_outliers: float
    total_outliers_alto: int
    total_outliers_bajo: int
    grupos_procesados: int
    estadisticas_por_grupo: list[EstadisticasGrupoResponse]
    fecha_calculo: datetime