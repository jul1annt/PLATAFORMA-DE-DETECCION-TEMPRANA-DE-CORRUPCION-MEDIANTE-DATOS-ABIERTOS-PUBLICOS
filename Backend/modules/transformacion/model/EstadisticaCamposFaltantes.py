from sqlalchemy import Column, BigInteger, Integer, String, DateTime, UniqueConstraint, Index, Numeric
from sqlalchemy.sql import func
from shared.base_model import Base


class EstadisticaCamposFaltantes(Base):
    """
    Conteo reconstruible de contratos procesados con cada campo obligatorio ausente.
    El porcentaje usa como denominador todos los contratos procesados vigentes.
    """
    __tablename__ = "estadistica_campos_faltantes"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    nombre_campo    = Column(String(100), nullable=False, unique=True, index=True)
    contador_faltantes = Column(Integer,  nullable=False, default=0)
    porcentaje_total = Column(Numeric(5, 2), default=0.0)
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
