from pydantic import BaseModel
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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True