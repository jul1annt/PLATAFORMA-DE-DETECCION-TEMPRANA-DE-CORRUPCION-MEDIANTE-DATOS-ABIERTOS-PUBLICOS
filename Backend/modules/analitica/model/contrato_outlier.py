import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base


class ContratoOutlier(Base):
    """
    Tabla de salida del análisis estadístico IQR.
    Almacena un registro por cada contrato analizado en cada ejecución.
    NO es fuente de datos, es resultado de procesamiento.
    """
    __tablename__ = "contrato_outlier"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Referencia al contrato analizado (no FK hard para no acoplar módulos)
    contrato_id = Column(UUID(as_uuid=True), nullable=False)

    # Identificador de la ejecución del análisis (agrupa todos los resultados de un mismo run)
    run_id = Column(UUID(as_uuid=True), nullable=False)

    # Agrupación estadística usada (valor de modalidad_de_contratacion o tipo_de_contrato)
    grupo = Column(String(255), nullable=False)

    # Campo numérico que se analizó
    campo_analizado = Column(String(100), nullable=False, default="valor_total_normalizado")

    # Valor del contrato en el momento del análisis
    valor = Column(Numeric(20, 2), nullable=False)

    # Estadísticas del grupo al que pertenece el contrato
    q1 = Column(Numeric(20, 2), nullable=False)
    q3 = Column(Numeric(20, 2), nullable=False)
    iqr = Column(Numeric(20, 2), nullable=False)
    limite_inferior = Column(Numeric(20, 2), nullable=False)
    limite_superior = Column(Numeric(20, 2), nullable=False)

    # Resultado de la clasificación
    es_outlier = Column(Boolean, nullable=False, default=False)

    # 'ALTO' si valor > limite_superior, 'BAJO' si valor < limite_inferior, NULL si no es outlier
    direccion_outlier = Column(String(10), nullable=True)

    # Cuántas veces el IQR sobrepasa el límite correspondiente.
    # Outlier alto: (valor - limite_superior) / IQR
    # Outlier bajo: (limite_inferior - valor) / IQR
    # No outlier:   0
    score = Column(Numeric(10, 4), nullable=False, default=0)

    fecha_calculo = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_contrato_outlier_run_id", "run_id"),
        Index("ix_contrato_outlier_contrato_id", "contrato_id"),
        Index("ix_contrato_outlier_es_outlier", "es_outlier"),
        Index("ix_contrato_outlier_grupo", "grupo"),
    )