from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SAEnum
from sqlalchemy.sql import func
from shared.base_model import Base
from shared.enums import TipoFormato

class FuenteDatos(Base):
    __tablename__ = "fuentes_datos"

    id              = Column(Integer, primary_key=True, index=True)
    nombre          = Column(String(100), nullable=False, unique=True)
    tipo            = Column(String(50), nullable=False)
    formato         = Column(SAEnum(TipoFormato), nullable=False)        # <-- nuevo
    endpoint        = Column(Text, nullable=False)
    api_key         = Column(Text, nullable=True)
    frecuencia_dias = Column(Integer, nullable=False, default=15)
    activo          = Column(Boolean, default=True)
    ultima_sync     = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())