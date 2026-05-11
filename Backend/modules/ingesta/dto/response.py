from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from shared.enums import TipoFormato

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