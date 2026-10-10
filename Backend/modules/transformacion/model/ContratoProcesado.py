from sqlalchemy import Column, BigInteger, String, Text, Numeric, Date, DateTime, ForeignKey, Index, Boolean, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
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
    raw_secop_id = Column(BigInteger, ForeignKey("raw_secop.id"), nullable=False, unique=True, index=True)

    # Campos normalizados — nombres explícitos para diferenciarlos de los crudos
    id_del_proceso               = Column(String(100),  index=True)
    entidad_normalizada          = Column(Text,          index=True)
    nit_entidad                  = Column(String(50))
    proveedor_normalizado        = Column(Text,          index=True)
    nit_proveedor                = Column(String(50))
    nit_proveedor_clave           = Column(String(15),    index=True)
    fecha_publicacion_normalizada = Column(Date,         index=True)
    fecha_adjudicacion_normalizada = Column(Date,        index=True)
    valor_total_normalizado      = Column(Numeric(38, 2), index=True)
    precio_base_normalizado      = Column(Numeric(38, 2))
    tipo_contrato_normalizado    = Column(String(200),   index=True)
    modalidad_contratacion       = Column(String(200))
    estado_normalizado           = Column(String(100))
    ciudad_entidad               = Column(String(100))
    departamento_entidad         = Column(String(100))
    urlproceso                   = Column(Text)

    # Control de integridad
    normalized_hash = Column(String(64), nullable=False, index=True)

    # Identificación de registros incompletos
    es_incompleto = Column(Boolean, default=False, index=True)
    cantidad_campos_faltantes = Column(Integer, default=0)
    campos_faltantes = Column(JSONB, default=list)
    nivel_confianza = Column(Integer, default=100, index=True)

    # Identificación de registros sospechosos
    es_sospechoso = Column(Boolean, default=False, index=True)

    # Última clasificación autoritativa calculada por el backend.
    clasificacion_riesgo = Column(String(20), nullable=False, default="SIN_EVALUAR", index=True)
    score_riesgo = Column(Numeric(20, 4), nullable=True)
    riesgo_run_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    procesado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_cp_entidad_fecha", "entidad_normalizada", "fecha_publicacion_normalizada"),
        Index("ix_cp_tipo_valor",    "tipo_contrato_normalizado", "valor_total_normalizado"),
        Index(
            "ix_cp_metricas_cover",
            "es_incompleto", "es_sospechoso", "clasificacion_riesgo", "nivel_confianza",
            postgresql_include=["id"],
        ),
        Index(
            "ix_cp_nit_nombre", "nit_proveedor_clave", "proveedor_normalizado",
            postgresql_where=nit_proveedor_clave.is_not(None),
        ),
    )
