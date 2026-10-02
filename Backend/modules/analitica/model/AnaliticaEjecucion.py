import uuid

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from shared.base_model import Base


class AnaliticaEjecucion(Base):
    """Durable status and input scope for every analytics execution."""

    __tablename__ = "analitica_ejecuciones"

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo = Column(String(32), nullable=False, index=True)
    estado = Column(String(24), nullable=False, index=True)
    parametros = Column(JSONB, nullable=False, default=dict)
    universo = Column(JSONB, nullable=False, default=dict)
    firma_universo = Column(JSONB, nullable=False, default=dict)
    fecha_inicio = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    fecha_fin = Column(DateTime(timezone=True), nullable=True)
    total_contratos = Column(BigInteger, nullable=False, default=0)
    total_resultados = Column(BigInteger, nullable=True)
    error_id = Column(UUID(as_uuid=True), nullable=True)
    mensaje_error = Column(Text, nullable=True)
