from sqlalchemy import Column, String, Integer, Numeric, Text, ForeignKey, Date, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base

# Providing skeletal models for the existing database just to prepare for future scalability
# For Epic 1, these won't be actively written to by our ingestion endpoint (raw data goes to datos_crudos first),
# but they are here to ensure we don't 'reinvent the database'.

class Ciudad(Base):
    __tablename__ = 'ciudad'
    id_ciudad = Column(Integer, primary_key=True, autoincrement=True)
    nombre_ciudad = Column(String(150), nullable=False)
    nombre_departamento = Column(String(150), nullable=False)

class Entidad(Base):
    __tablename__ = 'entidad'
    id_entidad = Column(Integer, primary_key=True, autoincrement=True)
    nit_entidad = Column(String(20), nullable=False, unique=True)
    nombre_entidad = Column(Text, nullable=False)
    id_ciudad = Column(Integer, ForeignKey('ciudad.id_ciudad'))

class Proceso(Base):
    __tablename__ = 'proceso'
    id_proceso = Column(String(100), primary_key=True)
    referencia_proceso = Column(String(100))
    precio_base = Column(Numeric(20, 2))
    estado_procedimiento = Column(String(150))
    id_entidad = Column(Integer, ForeignKey('entidad.id_entidad'), nullable=False)
    # Add other fields as necessary for scaling
