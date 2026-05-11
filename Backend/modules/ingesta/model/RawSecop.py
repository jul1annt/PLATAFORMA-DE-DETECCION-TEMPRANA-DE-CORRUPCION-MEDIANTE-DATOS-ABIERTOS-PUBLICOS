from sqlalchemy import (
    Column, Integer, String, Text, Numeric,
    DateTime, Index, BigInteger, ForeignKey
)
from sqlalchemy.sql import func
from shared.base_model import Base

class RawSecop(Base):
    __tablename__ = "raw_secop"

    id                              = Column(BigInteger, primary_key=True, autoincrement=True)
    fuente_id                       = Column(Integer, ForeignKey("fuentes_datos.id"), nullable=False)

    # Entidad
    entidad                         = Column(Text)
    nit_entidad                     = Column(String(50))
    departamento_entidad            = Column(String(100))
    ciudad_entidad                  = Column(String(100))
    ordenentidad                    = Column(Text)
    codigo_pci                      = Column(String(50))
    codigo_entidad                  = Column(Numeric)

    # Proceso
    id_del_proceso                  = Column(String(100))
    referencia_del_proceso          = Column(Text)
    ppi                             = Column(Text)
    id_del_portafolio               = Column(String(100))
    nombre_del_procedimiento        = Column(Text)
    descripci_n_del_procedimiento   = Column(Text)
    fase                            = Column(String(100))
    estado_del_procedimiento        = Column(String(100))
    id_estado_del_procedimiento     = Column(Numeric)
    estado_de_apertura_del_proceso  = Column(String(100))
    estado_resumen                  = Column(String(100))

    # Fechas
    fecha_de_publicacion_del        = Column(DateTime(timezone=True))
    fecha_de_ultima_publicaci       = Column(DateTime(timezone=True))
    fecha_de_publicacion_fase       = Column(DateTime(timezone=True))
    fecha_de_publicacion_fase_1     = Column(DateTime(timezone=True))
    fecha_de_publicacion            = Column(DateTime(timezone=True))
    fecha_de_publicacion_fase_2     = Column(DateTime(timezone=True))
    fecha_de_publicacion_fase_3     = Column(DateTime(timezone=True))
    fecha_de_recepcion_de           = Column(DateTime(timezone=True))
    fecha_de_apertura_de_respuesta  = Column(DateTime(timezone=True))
    fecha_de_apertura_efectiva      = Column(DateTime(timezone=True))
    fecha_adjudicacion              = Column(DateTime(timezone=True))

    # Contratación
    precio_base                     = Column(Numeric(20, 2))
    modalidad_de_contratacion       = Column(String(200))
    justificaci_n_modalidad_de      = Column(Text)
    duracion                        = Column(Numeric)
    unidad_de_duracion              = Column(String(50))
    tipo_de_contrato                = Column(String(200))
    subtipo_de_contrato             = Column(String(200))
    categorias_adicionales          = Column(Text)
    codigo_principal_de_categoria   = Column(String(100))

    # Unidad de contratación
    ciudad_de_la_unidad_de          = Column(String(100))
    nombre_de_la_unidad_de          = Column(Text)

    # Métricas
    proveedores_invitados           = Column(Numeric)
    proveedores_con_invitacion      = Column(Numeric)
    visualizaciones_del             = Column(Numeric)
    proveedores_que_manifestaron    = Column(Numeric)
    respuestas_al_procedimiento     = Column(Numeric)
    respuestas_externas             = Column(Numeric)
    conteo_de_respuestas_a_ofertas  = Column(Numeric)
    proveedores_unicos_con          = Column(Numeric)
    numero_de_lotes                 = Column(Numeric)

    # Adjudicación
    adjudicado                      = Column(String(10))
    id_adjudicacion                 = Column(String(100))
    codigoproveedor                 = Column(String(100))
    departamento_proveedor          = Column(String(100))
    ciudad_proveedor                = Column(String(100))
    valor_total_adjudicacion        = Column(Numeric(20, 2))
    nombre_del_adjudicador          = Column(Text)
    nombre_del_proveedor            = Column(Text)
    nit_del_proveedor_adjudicado    = Column(String(50))

    # URL
    urlproceso                      = Column(Text)

    # Auditoría
    sincronizado_en                 = Column(DateTime(timezone=True), server_default=func.now())

    # ── Índices optimizados para 8M de registros ──────────
    __table_args__ = (
        # Deduplicación: no insertar el mismo proceso dos veces
        Index("ix_raw_secop_id_proceso",       "id_del_proceso", unique=True),

        # Filtros más frecuentes en análisis
        Index("ix_raw_secop_fecha_pub",         "fecha_de_publicacion_del"),
        Index("ix_raw_secop_nit_entidad",       "nit_entidad"),
        Index("ix_raw_secop_entidad",           "entidad"),
        Index("ix_raw_secop_estado",            "estado_del_procedimiento"),
        Index("ix_raw_secop_modalidad",         "modalidad_de_contratacion"),
        Index("ix_raw_secop_fuente",            "fuente_id"),

        # Índice compuesto para queries de analítica (entidad + fecha)
        Index("ix_raw_secop_entidad_fecha",     "nit_entidad", "fecha_de_publicacion_del"),

        # Índice para adjudicaciones
        Index("ix_raw_secop_adjudicado",        "adjudicado", "valor_total_adjudicacion"),
    )