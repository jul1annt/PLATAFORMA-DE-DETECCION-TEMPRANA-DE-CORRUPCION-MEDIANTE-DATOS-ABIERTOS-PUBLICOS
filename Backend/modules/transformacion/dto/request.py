from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date
from decimal import Decimal

class ContratoProcesadoFilterDTO(BaseModel):
    entidad: Optional[str] = Field(None, description="Nombre o parte del nombre de la entidad pública")
    proveedor: Optional[str] = Field(None, description="Nombre o NIT del proveedor")
    fecha_inicio: Optional[date] = Field(None, description="Fecha mínima del contrato (YYYY-MM-DD)")
    fecha_fin: Optional[date] = Field(None, description="Fecha máxima del contrato (YYYY-MM-DD)")
    valor_min: Optional[Decimal] = Field(None, description="Valor mínimo del contrato")
    valor_max: Optional[Decimal] = Field(None, description="Valor máximo del contrato")
    tipo_contrato: Optional[str] = Field(None, description="Tipo de contrato (ej: Prestación de servicios)")

class ReprocesarRequestDTO(BaseModel):
    limite: int = Field(1000, ge=1, le=10000, description="Cantidad máxima de registros a procesar en esta ejecución")
    forzar_reproceso: bool = Field(False, description="Si es True, ignora si el registro ya fue procesado y lo evalúa de nuevo (útil para actualizaciones masivas)")
