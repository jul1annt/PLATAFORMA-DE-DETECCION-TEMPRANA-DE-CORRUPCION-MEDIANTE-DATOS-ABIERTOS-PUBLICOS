from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from shared.base_model import Base

class FuenteDatos(Base):
    __tablename__ = "fuentes_datos"

    id               = Column(Integer, primary_key=True, index=True)
    nombre           = Column(String(100), nullable=False, unique=True)
    tipo             = Column(String(50), nullable=False)          # SECOP, SISCON, etc.
    endpoint         = Column(Text, nullable=False)
    api_key          = Column(Text, nullable=True)                 # Encriptado en BD
    frecuencia_dias  = Column(Integer, nullable=False, default=15)
    activo           = Column(Boolean, default=True)
    ultima_sync      = Column(DateTime(timezone=True), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())