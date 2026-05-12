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
    motivo          = Column(String(50),  nullable=False)   # CAMPO_FALTANTE | FECHA_FUTURA | MONTO_NEGATIVO
    campo_afectado  = Column(String(100), nullable=False)   # nombre de la columna afectada
    valor_detectado = Column(Text)                          # valor crudo que disparó la anomalía (puede ser NULL)
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_cai_motivo",     "motivo"),
        Index("ix_cai_campo",      "campo_afectado"),
    )
