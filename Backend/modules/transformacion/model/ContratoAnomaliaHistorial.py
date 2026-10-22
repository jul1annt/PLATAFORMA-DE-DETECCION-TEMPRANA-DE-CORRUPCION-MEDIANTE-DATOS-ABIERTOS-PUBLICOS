from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text, UniqueConstraint, func

from shared.base_model import Base


class ContratoAnomaliaHistorial(Base):
    """Immutable record of an anomaly that is no longer in the active set."""

    __tablename__ = "contrato_anomalo_incompleto_historial"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    anomalia_id_original = Column(BigInteger, nullable=False)
    raw_secop_id = Column(BigInteger, nullable=False, index=True)
    id_contrato_procesado = Column(BigInteger, nullable=True, index=True)
    motivo = Column(String(50), nullable=True)
    valor_detectado = Column(Text, nullable=True)
    tipo_anomalia = Column(String(50), nullable=True)
    valor_original = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)
    campo_afectado = Column(String(100), nullable=False)
    fecha_inicio = Column(DateTime(timezone=True), nullable=False)
    fecha_fin = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("anomalia_id_original", name="uq_anomalia_historial_original"),
    )
