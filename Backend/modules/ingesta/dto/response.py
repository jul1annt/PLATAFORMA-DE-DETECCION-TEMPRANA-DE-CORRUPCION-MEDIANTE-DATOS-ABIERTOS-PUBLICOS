from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from shared.enums import TipoFormato
from modules.ingesta.model.SincronizacionHistorial import EstadoSync

class FuenteDatosResponseDTO(BaseModel):
    id: int
    nombre: str
    tipo: str
    formato: TipoFormato
    endpoint: str
    frecuencia_dias: int
    activo: bool
    ultima_sync: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConexionTestResponseDTO(BaseModel):
    exitoso: bool
    mensaje: str
    registros_muestra: Optional[int] = None

class SincronizacionHistorialResponseDTO(BaseModel):
    id:                   int
    fuente_id:            int
    fuente_nombre:        Optional[str] = None
    fecha_inicio:         datetime
    fecha_fin:            Optional[datetime]
    registros_traidos:    int
    registros_insertados: int
    registros_duplicados: int
    estado:               EstadoSync
    mensaje_error:        Optional[str]

    model_config = ConfigDict(from_attributes=True)


class SincronizacionHistorialResumenDTO(BaseModel):
    total: int
    exitoso: int
    en_proceso: int
    error: int
    parcial: int


class SincronizacionHistorialPaginaDTO(BaseModel):
    total: int
    page: int
    size: int
    items: list[SincronizacionHistorialResponseDTO]


class ComparativaFuenteDTO(BaseModel):
    fuente_id: int
    nombre: str
    endpoint: str
    ultima_sync_estado: Optional[EstadoSync]
    ultima_sync_error: Optional[str] = None
    total_traidos: int
    total_insertados: int
    total_duplicados: int
    tasa_duplicidad: float
