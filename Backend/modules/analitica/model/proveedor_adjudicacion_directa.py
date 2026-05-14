import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, Index, BigInteger, Integer, Date
from sqlalchemy.dialects.postgresql import UUID
from shared.base_model import Base


class ProveedorAdjudicacionDirecta(Base):
    """
    Tabla de salida del análisis de abuso de adjudicación directa.
    Almacena un registro por cada proveedor que supera el umbral de
    contratos directos en la ventana de tiempo analizada.
    NO es fuente de datos, es resultado de procesamiento.
    """
    __tablename__ = "proveedor_adjudicacion_directa"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identificador de la ejecución del análisis (agrupa todos los resultados de un mismo run)
    run_id = Column(UUID(as_uuid=True), nullable=False)

    # Referencia al contrato representativo del proveedor (no FK hard para no acoplar módulos)
    contrato_id = Column(BigInteger, nullable=True)

    # Información del proveedor desnormalizada para facilitar consultas sin joins
    proveedor = Column(String(500), nullable=False)
    nit_proveedor = Column(String(100), nullable=True)

    # Contexto adicional del contrato más reciente del proveedor
    entidad = Column(String(500), nullable=True)
    tipo_contrato = Column(String(255), nullable=True)
    modalidad_contratacion = Column(String(255), nullable=True)

    # Fecha del contrato más reciente del proveedor en el análisis
    fecha_contrato = Column(Date, nullable=True)

    # Métricas de adjudicación
    total_contratos = Column(Integer, nullable=False, default=0)
    contratos_directos = Column(Integer, nullable=False, default=0)

    # Porcentaje: (contratos_directos / total_contratos) * 100
    porcentaje_directos = Column(Numeric(6, 2), nullable=False, default=0)

    # Score: porcentaje_directos / 10  (rango 0-10)
    score_riesgo = Column(Numeric(6, 2), nullable=False, default=0)

    # 'ALTO' (>=90%), 'MEDIO' (70-89%), 'BAJO' (50-69%)
    clasificacion_riesgo = Column(String(50), nullable=False, default="BAJO")

    fecha_calculo = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_prov_adjdir_run_id", "run_id"),
        Index("ix_prov_adjdir_proveedor", "proveedor"),
        Index("ix_prov_adjdir_score_riesgo", "score_riesgo"),
        Index("ix_prov_adjdir_clasificacion_riesgo", "clasificacion_riesgo"),
        Index("ix_prov_adjdir_porcentaje_directos", "porcentaje_directos"),
    )
