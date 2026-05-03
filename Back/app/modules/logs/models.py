import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base

class LogSincronizacion(Base):
    __tablename__ = 'logs_sincronizacion'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fuente_id = Column(UUID(as_uuid=True), ForeignKey('fuentes_datos.id', ondelete='CASCADE'), nullable=False)
    fecha = Column(DateTime(timezone=True), server_default=func.now())
    estado = Column(String(50), nullable=False)
    cantidad_registros = Column(Integer, default=0)
    mensaje = Column(String)

    fuente = relationship("FuenteDatos", back_populates="logs")
