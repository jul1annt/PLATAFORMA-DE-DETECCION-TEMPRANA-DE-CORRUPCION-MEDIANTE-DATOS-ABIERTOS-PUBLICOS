from sqlalchemy import Column, BigInteger, String, Text, Numeric, Date, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func
from shared.base_model import Base


class ContratoProcesado(Base):
    """
    Tabla de contratos normalizados.
    Cada registro corresponde a un raw_secop procesado con datos limpios y estandarizados.
    """
    __tablename__ = "contratos_procesados"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Trazabilidad
    raw_secop_id = Column(BigInteger, ForeignKey("raw_secop.id"), nullable=False, index=True)

    # Campos normalizados — nombres explícitos para diferenciarlos de los crudos
    id_del_proceso               = Column(String(100),  index=True)
    entidad_normalizada          = Column(Text,          index=True)
    nit_entidad                  = Column(String(50))
    proveedor_normalizado        = Column(Text,          index=True)
    nit_proveedor                = Column(String(50))
    fecha_publicacion_normalizada = Column(Date,         index=True)
    fecha_adjudicacion_normalizada = Column(Date,        index=True)
    valor_total_normalizado      = Column(Numeric(20, 2), index=True)
    precio_base_normalizado      = Column(Numeric(20, 2))
    tipo_contrato_normalizado    = Column(String(200),   index=True)
    modalidad_contratacion       = Column(String(200))
    estado_normalizado           = Column(String(100))
    ciudad_entidad               = Column(String(100))
    departamento_entidad         = Column(String(100))
    urlproceso                   = Column(Text)

    # Control de integridad
    normalized_hash = Column(String(64), unique=True, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_cp_entidad_fecha", "entidad_normalizada", "fecha_publicacion_normalizada"),
        Index("ix_cp_tipo_valor",    "tipo_contrato_normalizado", "valor_total_normalizado"),
    )
