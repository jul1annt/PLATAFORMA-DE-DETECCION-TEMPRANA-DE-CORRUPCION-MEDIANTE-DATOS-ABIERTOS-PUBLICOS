from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from shared.enums import TipoFormato

class FuenteDatosCreateDTO(BaseModel):
    nombre: str            = Field(..., min_length=3, max_length=100)
    tipo: str              = Field(..., description="SECOP, SISCON, etc.")
    formato: TipoFormato   = Field(..., description="JSON, CSV o XML")
    endpoint: HttpUrl
    api_key: Optional[str] = None
    frecuencia_dias: int   = Field(default=15, ge=1, le=365)

class FuenteDatosUpdateDTO(BaseModel):
    nombre: Optional[str]          = None
    formato: Optional[TipoFormato] = None
    endpoint: Optional[HttpUrl]    = None
    api_key: Optional[str]         = None
    frecuencia_dias: Optional[int] = Field(default=None, ge=1, le=365)
    activo: Optional[bool]         = None