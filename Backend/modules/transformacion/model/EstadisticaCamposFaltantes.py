from sqlalchemy import Column, BigInteger, Integer, String, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func
from shared.base_model import Base


class EstadisticaCamposFaltantes(Base):
    """
    Contador acumulado de cuántas veces ha faltado cada campo obligatorio.
    Se incrementa en +1 por cada registro que llega sin ese campo.
    """
    __tablename__ = "estadistica_campos_faltantes"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    nombre_campo    = Column(String(100), nullable=False, unique=True, index=True)
    contador_faltantes = Column(Integer,  nullable=False, default=0)
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
