from sqlalchemy import Column, BigInteger, String, Text, Numeric, Date, DateTime, Index
from sqlalchemy.sql import func
from shared.base_model import Base

class ContratoProcesado(Base):
    __tablename__ = "contratos_procesados"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    raw_data_id = Column(BigInteger, index=True) # Reference to raw_secop.id
    id_proceso = Column(String(100), index=True)
    entidad = Column(Text, index=True)
    proveedor = Column(Text, index=True)
    valor_contrato = Column(Numeric(20, 2), index=True)
    fecha_contrato = Column(Date, index=True)
    tipo_contrato = Column(String(200), index=True)
    estado = Column(String(100))
    normalized_hash = Column(String(64), unique=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
