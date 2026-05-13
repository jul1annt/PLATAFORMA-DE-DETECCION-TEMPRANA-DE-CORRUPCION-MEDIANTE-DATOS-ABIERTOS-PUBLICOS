import uuid
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, Index, Integer, Date
from sqlalchemy.dialects.postgresql import UUID
from shared.base_model import Base


class ContratoDuplicadoPeriodo(Base):
    """
    Tabla de salida del análisis de contratos duplicados en un período corto.
    Almacena un registro por cada contrato que se adjudicó a un mismo proveedor,
    con la misma entidad y características similares, en un lapso menor a 30 días
    respecto a un contrato previo.
    NO es fuente de datos, es resultado de procesamiento.
    """
    __tablename__ = "contrato_duplicado_periodo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identificador de la ejecución del análisis
    run_id = Column(UUID(as_uuid=True), nullable=False)

    # Referencia al contrato principal y al contrato anterior con el que se compara
    contrato_id = Column(BigInteger, nullable=False)
    contrato_relacionado_id = Column(BigInteger, nullable=False)

    # Información desnormalizada para facilitar consultas sin joins complejos
    proveedor = Column(String(255), nullable=False)
    entidad = Column(String(255), nullable=False)
    tipo_contrato = Column(String(255), nullable=True)
    modalidad_contratacion = Column(String(255), nullable=True)

    # Fechas involucradas
    fecha_contrato = Column(Date, nullable=False)
    fecha_relacionada = Column(Date, nullable=False)

    # Resultados del cálculo
    diferencia_dias = Column(Integer, nullable=False)
    duplicado_score = Column(Numeric(10, 2), nullable=False)
    
    # Riesgo calculado: 'ALTO' (0-5 días), 'MEDIO' (6-15 días), 'BAJO' (16-30 días)
    clasificacion_riesgo = Column(String(50), nullable=False)

    fecha_calculo = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_contrato_duplicado_run_id", "run_id"),
        Index("ix_contrato_duplicado_contrato_id", "contrato_id"),
        Index("ix_contrato_duplicado_score", "duplicado_score"),
        Index("ix_contrato_duplicado_riesgo", "clasificacion_riesgo"),
    )
