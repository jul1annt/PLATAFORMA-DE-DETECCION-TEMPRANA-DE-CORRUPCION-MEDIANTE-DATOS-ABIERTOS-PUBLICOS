from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal

class ContratoProcesadoResponse(BaseModel):
    id: UUID
    id_proceso: str
    entidad: Optional[str]
    proveedor: Optional[str]
    valor: Optional[Decimal]
    fecha: Optional[date]
    tipo_contrato: Optional[str]
    fuente_id: UUID
    fecha_carga: datetime
    estado_calidad: str

    model_config = ConfigDict(from_attributes=True)

class CalidadDatosResponse(BaseModel):
    id: UUID
    contrato_id: UUID
    tipo_problema: str
    campo: Optional[str]
    descripcion: Optional[str]
    fecha: datetime

    model_config = ConfigDict(from_attributes=True)

class ResumenCalidadResponse(BaseModel):
    id: UUID
    fuente_id: UUID
    total_registros: int
    incompletos: int
    sospechosos: int
    fecha: datetime

    model_config = ConfigDict(from_attributes=True)

class CambiosContratosResponse(BaseModel):
    id: UUID
    id_proceso: str
    campo: str
    valor_anterior: Optional[str]
    valor_nuevo: Optional[str]
    fecha: datetime

    model_config = ConfigDict(from_attributes=True)

class ProcessResponse(BaseModel):
    status: str
    processed_count: int
    new_records: int
    updated_records: int
    issues_found: int
