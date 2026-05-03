import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric, Text, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.models.base import Base

class ContratoProcesado(Base):
    __tablename__ = 'contratos_procesados'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_proceso = Column(String(100), nullable=False)
    entidad = Column(Text)
    proveedor = Column(Text)
    valor = Column(Numeric(20,2))
    fecha = Column(Date)
    tipo_contrato = Column(Text)
    fuente_id = Column(UUID(as_uuid=True), ForeignKey('fuentes_datos.id', ondelete='CASCADE'), nullable=False)
    fecha_carga = Column(DateTime(timezone=True), server_default=func.now())
    hash_procesado = Column(String(64), unique=True, nullable=False)
    estado_calidad = Column(String(20), nullable=False, default='OK')

class CalidadDatos(Base):
    __tablename__ = 'calidad_datos'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contrato_id = Column(UUID(as_uuid=True), ForeignKey('contratos_procesados.id', ondelete='CASCADE'), nullable=False)
    tipo_problema = Column(String(50), nullable=False)
    campo = Column(String(100))
    descripcion = Column(Text)
    fecha = Column(DateTime(timezone=True), server_default=func.now())

class ResumenCalidad(Base):
    __tablename__ = 'resumen_calidad'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fuente_id = Column(UUID(as_uuid=True), ForeignKey('fuentes_datos.id', ondelete='CASCADE'), nullable=False)
    total_registros = Column(Integer, default=0)
    incompletos = Column(Integer, default=0)
    sospechosos = Column(Integer, default=0)
    fecha = Column(DateTime(timezone=True), server_default=func.now())

class CambiosContratos(Base):
    __tablename__ = 'cambios_contratos'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_proceso = Column(String(100), nullable=False)
    campo = Column(String(100), nullable=False)
    valor_anterior = Column(Text)
    valor_nuevo = Column(Text)
    fecha = Column(DateTime(timezone=True), server_default=func.now())
