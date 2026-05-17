from sqlalchemy import Column, BigInteger, String, Text, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from shared.base_model import Base

class ProcesamientoLog(Base):
    """
    Tabla de registro histórico de ejecuciones del pipeline de normalización.
    """
    __tablename__ = "procesamiento_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Resultados y métricas de la ejecución
    total_evaluados = Column(Integer, default=0)
    procesados = Column(Integer, default=0)
    omitidos = Column(Integer, default=0)
    anomalias_registradas = Column(Integer, default=0)

    # Tiempos de ejecución
    fecha_hora_inicio = Column(DateTime(timezone=True), nullable=False)
    fecha_hora_fin = Column(DateTime(timezone=True), nullable=True)
    duracion_segundos = Column(Integer, nullable=True)

    # Parámetros y estado
    forzar_reproceso = Column(Boolean, default=False)
    estado = Column(String(50), nullable=False) # EN_PROCESO, EXITOSO, ERROR
    mensaje_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
