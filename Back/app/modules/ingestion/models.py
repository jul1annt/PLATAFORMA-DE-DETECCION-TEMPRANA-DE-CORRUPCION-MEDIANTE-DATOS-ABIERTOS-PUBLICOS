import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base

class DatoCrudo(Base):
    __tablename__ = 'datos_crudos'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fuente_id = Column(UUID(as_uuid=True), ForeignKey('fuentes_datos.id', ondelete='CASCADE'), nullable=False)
    hash_registro = Column(String(64), unique=True, nullable=False)
    datos_json = Column(JSONB, nullable=False)
    fecha_carga = Column(DateTime(timezone=True), server_default=func.now())

    fuente = relationship("FuenteDatos", back_populates="datos_crudos")
