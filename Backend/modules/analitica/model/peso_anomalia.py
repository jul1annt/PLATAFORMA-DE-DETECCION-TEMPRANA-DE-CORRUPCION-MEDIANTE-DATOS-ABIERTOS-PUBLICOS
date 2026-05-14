from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.sql import func
from shared.base_model import Base

class PesoAnomalia(Base):
    """
    Configuración de pesos para cada tipo de anomalía detectada en analítica.
    """
    __tablename__ = "peso_anomalia"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_anomalia = Column(String(50), unique=True, nullable=False, index=True)
    peso = Column(Numeric(5, 2), nullable=False, default=1.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
