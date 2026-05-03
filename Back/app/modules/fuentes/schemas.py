from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

class FuenteDatosBase(BaseModel):
    nombre: str
    tipo: str
    endpoint: Optional[str] = None
    frecuencia_dias: int = 1
    estado: str = 'activa'

class FuenteDatosCreate(FuenteDatosBase):
    pass

class FuenteDatosUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    endpoint: Optional[str] = None
    frecuencia_dias: Optional[int] = None

class FuenteDatosResponse(FuenteDatosBase):
    id: UUID
    ultima_sincronizacion: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
