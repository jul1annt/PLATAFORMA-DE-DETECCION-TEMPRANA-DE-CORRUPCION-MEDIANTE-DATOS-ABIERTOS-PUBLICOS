from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

class ContratoProcesadoResponseDTO(BaseModel):
    id: int = Field(..., description="ID único del registro procesado")
    raw_data_id: Optional[int] = Field(None, description="Referencia al ID original en la tabla raw_secop")
    id_proceso: Optional[str] = Field(None, description="Identificador único del proceso de contratación")
    entidad: Optional[str] = Field(None, description="Nombre normalizado de la entidad")
    proveedor: Optional[str] = Field(None, description="Nombre normalizado del proveedor")
    valor_contrato: Optional[Decimal] = Field(None, description="Monto del contrato en formato numérico")
    fecha_contrato: Optional[date] = Field(None, description="Fecha del contrato en formato ISO (YYYY-MM-DD)")
    tipo_contrato: Optional[str] = Field(None, description="Categoría o tipo de contrato")
    estado: Optional[str] = Field(None, description="Estado actual del proceso")
    normalized_hash: Optional[str] = Field(None, description="Hash SHA256 único generado a partir de los datos normalizados")
    created_at: datetime = Field(..., description="Fecha de creación del registro")
    updated_at: datetime = Field(..., description="Fecha de última actualización")

    model_config = ConfigDict(from_attributes=True)

class PaginatedResponseDTO(BaseModel):
    total: int
    page: int
    size: int
    items: List[ContratoProcesadoResponseDTO]
