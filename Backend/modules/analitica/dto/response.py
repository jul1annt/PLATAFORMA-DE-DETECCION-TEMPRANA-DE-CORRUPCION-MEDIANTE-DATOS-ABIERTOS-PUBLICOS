from datetime import datetime, date
from decimal import Decimal
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


class DuplicadoDetalleResponse(BaseModel):
    """Un contrato duplicado con su clasificación y score."""
    id: UUID
    run_id: UUID
    contrato_id: int
    contrato_relacionado_id: int
    proveedor: str
    entidad: str
    tipo_contrato: Optional[str]
    modalidad_contratacion: Optional[str]
    fecha_contrato: date
    fecha_relacionada: date
    diferencia_dias: int
    duplicado_score: float
    clasificacion_riesgo: str
    fecha_calculo: datetime

    class Config:
        from_attributes = True

class DuplicadoListaResponse(BaseModel):
    """Respuesta paginada del listado de duplicados."""
    items: list[DuplicadoDetalleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class RiesgoResumenResponse(BaseModel):
    """Resumen estadístico por nivel de riesgo."""
    riesgo: str
    total: int

class DuplicadoResumenResponse(BaseModel):
    """Resumen de una ejecución completa del análisis de duplicados."""
    run_id: UUID
    total_duplicados: int
    promedio_dias_diferencia: float
    promedio_score: float
    resumen_por_riesgo: list[RiesgoResumenResponse]
    fecha_calculo: datetime


# ============================================================
# ADJUDICACIÓN DIRECTA
# ============================================================

class ProveedorDirectaDetalleResponse(BaseModel):
    """Un proveedor con su clasificación de abuso de adjudicación directa."""
    id: UUID
    run_id: UUID
    contrato_id: Optional[int]
    proveedor: str
    nit_proveedor: Optional[str]
    entidad: Optional[str]
    tipo_contrato: Optional[str]
    modalidad_contratacion: Optional[str]
    fecha_contrato: Optional[date]
    total_contratos: int
    contratos_directos: int
    porcentaje_directos: float
    score_riesgo: float
    clasificacion_riesgo: str
    fecha_calculo: datetime

    class Config:
        from_attributes = True


class ProveedorDirectaListaResponse(BaseModel):
    """Respuesta paginada del listado de proveedores con abuso de directas."""
    items: list[ProveedorDirectaDetalleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ProveedorDirectaResumenResponse(BaseModel):
    """Resumen estadístico global de una ejecución de análisis de directas."""
    run_id: UUID
    total_proveedores_detectados: int
    promedio_porcentaje_directos: float
    promedio_score: float
    resumen_por_riesgo: list[RiesgoResumenResponse]
    fecha_calculo: datetime


# ============================================================
# RIESGO COMBINADO Y PESOS
# ============================================================

class PesoAnomaliaResponse(BaseModel):
    tipo_anomalia: str
    peso: Decimal
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class RiesgoProveedorResponse(BaseModel):
    id: UUID
    run_id: UUID
    proveedor: str
    nit_proveedor: Optional[str]
    max_score_outlier: float
    max_score_duplicado: float
    score_directo: float
    score_final: float
    clasificacion_riesgo: str
    pesos_aplicados: dict
    fecha_calculo: datetime

    class Config:
        from_attributes = True

class RiesgoProveedorListaResponse(BaseModel):
    items: list[RiesgoProveedorResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class RiesgoGlobalResumenResponse(BaseModel):
    run_id: UUID
    total_proveedores_evaluados: int
    promedio_score_final: float
    resumen_por_riesgo: list[RiesgoResumenResponse]
    fecha_calculo: datetime
