from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, JSON, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func

from shared.base_model import Base


class RawSecopHistorial(Base):
    """Immutable snapshot of a raw SECOP row before a source-driven update."""

    __tablename__ = "raw_secop_historial"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    raw_secop_id = Column(BigInteger, nullable=False)
    id_del_proceso = Column(String(100), nullable=True)
    fuente_id = Column(Integer, nullable=False)
    datos_anteriores = Column(JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False)
    archivado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_raw_secop_historial_raw_id", "raw_secop_id"),
        Index("ix_raw_secop_historial_proceso", "id_del_proceso"),
    )
