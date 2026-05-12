from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from shared.base_model import Base


class ContratoAnomaloIncompleto(Base):
    """
    Registra anomalías detectadas durante el proceso de normalización.
    Un registro puede tener múltiples anomalías (una por motivo/campo).
    """
    __tablename__ = "contrato_anomalo_incompleto"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    raw_secop_id    = Column(BigInteger, ForeignKey("raw_secop.id"), nullable=False, index=True)
    id_contrato_procesado = Column(BigInteger, ForeignKey("contratos_procesados.id"), nullable=True, index=True)
    
    # Legacy fields (mantener por retrocompatibilidad)
    motivo          = Column(String(50),  nullable=True)    # CAMPO_FALTANTE | FECHA_FUTURA | MONTO_NEGATIVO
    valor_detectado = Column(Text, nullable=True)           # valor crudo que disparó la anomalía
    
    # Nuevos fields
    tipo_anomalia   = Column(String(50), nullable=True)     # Reemplaza a motivo
    valor_original  = Column(Text, nullable=True)           # Reemplaza a valor_detectado
    descripcion     = Column(Text, nullable=True)           # Ej. "El contrato no contiene valor_total_adjudicacion"
    
    campo_afectado  = Column(String(100), nullable=False)   # nombre de la columna afectada
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_cai_motivo",     "motivo"),
        Index("ix_cai_campo",      "campo_afectado"),
    )
