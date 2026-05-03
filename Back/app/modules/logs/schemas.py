from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

class LogSincronizacionResponse(BaseModel):
    id: UUID
    fuente_id: UUID
    fecha: datetime
    estado: str
    cantidad_registros: int
    mensaje: Optional[str]

    model_config = ConfigDict(from_attributes=True)
