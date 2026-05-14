from sqlalchemy import Column, String, Numeric, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from shared.base_model import Base
import uuid

class RiesgoProveedor(Base):
    """
    Registro del riesgo combinado por proveedor después de cruzar todas las anomalías.
    """
    __tablename__ = "riesgo_proveedor"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    proveedor = Column(String, nullable=False, index=True)
    nit_proveedor = Column(String(50), nullable=True)
    
    max_score_outlier = Column(Numeric, nullable=False, default=0.0)
    max_score_duplicado = Column(Numeric, nullable=False, default=0.0)
    score_directo = Column(Numeric, nullable=False, default=0.0)
    
    score_final = Column(Numeric, nullable=False, default=0.0, index=True)
    clasificacion_riesgo = Column(String(20), nullable=False, index=True)
    
    pesos_aplicados = Column(JSONB, nullable=False)
    fecha_calculo = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_riesgo_proveedor_score", "score_final", "clasificacion_riesgo"),
    )
