from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from shared.base_model import Base
import enum

class EstadoSync(str, enum.Enum):
    EN_PROCESO = "EN_PROCESO"
    EXITOSO    = "EXITOSO"
    ERROR      = "ERROR"

class SincronizacionHistorial(Base):
    __tablename__ = "sincronizacion_historial"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    fuente_id            = Column(Integer, ForeignKey("fuentes_datos.id"), nullable=False)
    fecha_inicio         = Column(DateTime(timezone=True), server_default=func.now())
    fecha_fin            = Column(DateTime(timezone=True), nullable=True)
    registros_traidos    = Column(BigInteger, default=0)
    registros_insertados = Column(BigInteger, default=0)
    registros_duplicados = Column(BigInteger, default=0)
    estado               = Column(SAEnum(EstadoSync), default=EstadoSync.EN_PROCESO)
    mensaje_error        = Column(Text, nullable=True)