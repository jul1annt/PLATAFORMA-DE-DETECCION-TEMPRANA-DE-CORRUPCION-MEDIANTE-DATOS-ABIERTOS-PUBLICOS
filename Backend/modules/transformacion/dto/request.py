from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date
from decimal import Decimal


class ContratoProcesadoFilterDTO(BaseModel):
    """Filtros disponibles para búsqueda en contratos_procesados"""
    entidad: Optional[str] = Field(None, description="Nombre o parte del nombre de la entidad pública")
    proveedor: Optional[str] = Field(None, description="Nombre o NIT del proveedor")
    tipo_contrato: Optional[str] = Field(None, description="Tipo de contrato (ej: Prestación de servicios)")
    estado: Optional[str] = Field(None, description="Estado del procedimiento")
    fecha_inicio: Optional[date] = Field(None, description="Fecha mínima de publicación (YYYY-MM-DD)")
    fecha_fin: Optional[date] = Field(None, description="Fecha máxima de publicación (YYYY-MM-DD)")
    valor_min: Optional[Decimal] = Field(None, description="Valor mínimo del contrato", ge=0)
    valor_max: Optional[Decimal] = Field(None, description="Valor máximo del contrato", ge=0)


class AnomaliaFilterDTO(BaseModel):
    """Filtros disponibles para búsqueda de anomalías"""
    raw_secop_id: Optional[int] = Field(None, description="Filtrar por ID de registro crudo")
    motivo: Optional[str] = Field(None, description="CAMPO_FALTANTE | FECHA_FUTURA | MONTO_NEGATIVO")
    campo_afectado: Optional[str] = Field(None, description="Nombre del campo afectado")


class ReprocesarRequestDTO(BaseModel):
    """Parámetros para el endpoint de reprocesamiento"""
    limite: int = Field(
        1000, ge=1, le=10000,
        description="Cantidad máxima de registros crudos a procesar en esta ejecución"
    )
    forzar_reproceso: bool = Field(
        False,
        description=(
            "false (default): solo procesa registros que aún no existen en contratos_procesados. "
            "true: ignora si el registro ya fue procesado y lo evalúa de nuevo, "
            "útil cuando cambia la lógica de normalización."
        )
    )
