import uuid
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base

class FuenteDatos(Base):
    __tablename__ = 'fuentes_datos'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(255), nullable=False)
    tipo = Column(String(50), nullable=False)
    endpoint = Column(String)
    frecuencia_dias = Column(Integer, default=1)
    estado = Column(String(50), default='activa')
    ultima_sincronizacion = Column(DateTime(timezone=True))

    datos_crudos = relationship("DatoCrudo", back_populates="fuente", cascade="all, delete-orphan")
    logs = relationship("LogSincronizacion", back_populates="fuente", cascade="all, delete-orphan")
