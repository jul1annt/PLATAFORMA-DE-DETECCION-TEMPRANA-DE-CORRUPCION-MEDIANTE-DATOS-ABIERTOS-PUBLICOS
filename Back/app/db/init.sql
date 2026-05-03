-- ── Extensión ────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── 1. Catálogos independientes ───────────────────────────────────

CREATE TABLE IF NOT EXISTS ciudad (
    id_ciudad           SERIAL       PRIMARY KEY,
    nombre_ciudad       VARCHAR(150) NOT NULL,
    nombre_departamento VARCHAR(150) NOT NULL,
    CONSTRAINT uq_ciudad UNIQUE (nombre_ciudad, nombre_departamento)
);

CREATE TABLE IF NOT EXISTS modalidad_contratacion (
    id_modalidad     SERIAL       PRIMARY KEY,
    nombre_modalidad VARCHAR(250) NOT NULL UNIQUE,
    justificacion    TEXT
);

CREATE TABLE IF NOT EXISTS procedimiento (
    id_procedimiento     SERIAL  PRIMARY KEY,
    nombre_procedimiento TEXT    NOT NULL,
    descripcion          TEXT,
    fase                 VARCHAR(100),
    CONSTRAINT uq_procedimiento UNIQUE (nombre_procedimiento, fase)
);

CREATE TABLE IF NOT EXISTS categoria (
    id_categoria     SERIAL      PRIMARY KEY,
    codigo_categoria VARCHAR(50) NOT NULL UNIQUE,
    descripcion      TEXT
);

-- ── 2. Entidades participantes ────────────────────────────────────

CREATE TABLE IF NOT EXISTS entidad (
    id_entidad     SERIAL      PRIMARY KEY,
    nit_entidad    VARCHAR(20) NOT NULL UNIQUE,
    nombre_entidad TEXT        NOT NULL,
    codigo_entidad VARCHAR(50),
    orden_entidad  VARCHAR(100),
    codigo_pci     VARCHAR(50),
    id_ciudad      INT         NOT NULL,
    CONSTRAINT fk_entidad_ciudad FOREIGN KEY (id_ciudad)
        REFERENCES ciudad(id_ciudad) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS proveedor (
    id_proveedor     SERIAL      PRIMARY KEY,
    codigo_proveedor VARCHAR(50),
    nit_proveedor    VARCHAR(20) NOT NULL UNIQUE,
    nombre_proveedor TEXT        NOT NULL,
    id_ciudad        INT,
    CONSTRAINT fk_proveedor_ciudad FOREIGN KEY (id_ciudad)
        REFERENCES ciudad(id_ciudad) ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS unidad_compradora (
    id_unidad     SERIAL PRIMARY KEY,
    nombre_unidad TEXT   NOT NULL UNIQUE,
    id_ciudad     INT,
    CONSTRAINT fk_unidad_ciudad FOREIGN KEY (id_ciudad)
        REFERENCES ciudad(id_ciudad) ON UPDATE CASCADE ON DELETE SET NULL
);

-- ── 3. Proceso (tabla central) ────────────────────────────────────

CREATE TABLE IF NOT EXISTS proceso (
    id_proceso              VARCHAR(100) PRIMARY KEY,
    referencia_proceso      VARCHAR(100),
    ppi                     VARCHAR(100),
    id_portafolio           VARCHAR(100),
    precio_base             NUMERIC(20,2),
    duracion                INT,
    unidad_duracion         VARCHAR(50),
    numero_lotes            INT          DEFAULT 0,
    estado_procedimiento    VARCHAR(150),
    id_estado_procedimiento INT,
    estado_apertura         VARCHAR(100),
    estado_resumen          VARCHAR(100),
    tipo_contrato           VARCHAR(100),
    subtipo_contrato        VARCHAR(100),
    url_proceso             TEXT,
    id_entidad              INT          NOT NULL,
    id_modalidad            INT,
    id_unidad               INT,
    id_procedimiento        INT,
    CONSTRAINT fk_proceso_entidad       FOREIGN KEY (id_entidad)
        REFERENCES entidad(id_entidad)           ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_proceso_modalidad     FOREIGN KEY (id_modalidad)
        REFERENCES modalidad_contratacion(id_modalidad) ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_proceso_unidad        FOREIGN KEY (id_unidad)
        REFERENCES unidad_compradora(id_unidad)  ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_proceso_procedimiento FOREIGN KEY (id_procedimiento)
        REFERENCES procedimiento(id_procedimiento) ON UPDATE CASCADE ON DELETE SET NULL
);

-- ── 4. Tablas dependientes de proceso ─────────────────────────────

CREATE TABLE IF NOT EXISTS fase_publicacion (
    id_fase                    SERIAL       PRIMARY KEY,
    id_proceso                 VARCHAR(100) NOT NULL,
    fecha_publicacion          DATE,
    fecha_ultima_publicacion   DATE,
    fecha_fase_1               DATE,
    fecha_fase_2               DATE,
    fecha_fase_3               DATE,
    fecha_recepcion_documentos DATE,
    fecha_apertura_respuestas  DATE,
    fecha_apertura_efectiva    DATE,
    CONSTRAINT fk_fase_proceso FOREIGN KEY (id_proceso)
        REFERENCES proceso(id_proceso) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metricas_proceso (
    id_metrica                 SERIAL       PRIMARY KEY,
    id_proceso                 VARCHAR(100) NOT NULL UNIQUE,
    proveedores_invitados      INT          DEFAULT 0,
    proveedores_con_invitacion INT          DEFAULT 0,
    visualizaciones            INT          DEFAULT 0,
    proveedores_manifestaron   INT          DEFAULT 0,
    respuestas_procedimiento   INT          DEFAULT 0,
    respuestas_externas        INT          DEFAULT 0,
    conteo_respuestas_ofertas  INT          DEFAULT 0,
    proveedores_unicos         INT          DEFAULT 0,
    actualizado_en             TIMESTAMPTZ  DEFAULT NOW(),
    CONSTRAINT fk_metricas_proceso FOREIGN KEY (id_proceso)
        REFERENCES proceso(id_proceso) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS adjudicacion (
    id_adjudicacion    VARCHAR(100) PRIMARY KEY,
    id_proceso         VARCHAR(100) NOT NULL,
    id_proveedor       INT,
    adjudicado         BOOLEAN      DEFAULT FALSE,
    fecha_adjudicacion DATE,
    valor_total        NUMERIC(20,2),
    nombre_adjudicador TEXT,
    CONSTRAINT fk_adj_proceso   FOREIGN KEY (id_proceso)
        REFERENCES proceso(id_proceso)   ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_adj_proveedor FOREIGN KEY (id_proveedor)
        REFERENCES proveedor(id_proveedor) ON UPDATE CASCADE ON DELETE SET NULL
);

-- ── 5. Relación N:M proceso ↔ categoría ──────────────────────────

CREATE TABLE IF NOT EXISTS proceso_categoria (
    id_proceso   VARCHAR(100) NOT NULL,
    id_categoria INT          NOT NULL,
    es_principal BOOLEAN      DEFAULT FALSE,
    PRIMARY KEY (id_proceso, id_categoria),
    CONSTRAINT fk_pc_proceso   FOREIGN KEY (id_proceso)
        REFERENCES proceso(id_proceso)    ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_pc_categoria FOREIGN KEY (id_categoria)
        REFERENCES categoria(id_categoria) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ── 6. Índices ────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_proceso_entidad    ON proceso(id_entidad);
CREATE INDEX IF NOT EXISTS idx_proceso_modalidad  ON proceso(id_modalidad);
CREATE INDEX IF NOT EXISTS idx_proceso_estado     ON proceso(estado_procedimiento);
CREATE INDEX IF NOT EXISTS idx_proceso_tipo       ON proceso(tipo_contrato);
CREATE INDEX IF NOT EXISTS idx_entidad_nit        ON entidad(nit_entidad);
CREATE INDEX IF NOT EXISTS idx_entidad_ciudad     ON entidad(id_ciudad);
CREATE INDEX IF NOT EXISTS idx_proveedor_nit      ON proveedor(nit_proveedor);
CREATE INDEX IF NOT EXISTS idx_fase_proceso       ON fase_publicacion(id_proceso);
CREATE INDEX IF NOT EXISTS idx_fase_fecha         ON fase_publicacion(fecha_publicacion);
CREATE INDEX IF NOT EXISTS idx_metricas_proceso   ON metricas_proceso(id_proceso);
CREATE INDEX IF NOT EXISTS idx_adj_proceso        ON adjudicacion(id_proceso);
CREATE INDEX IF NOT EXISTS idx_adj_proveedor      ON adjudicacion(id_proveedor);
CREATE INDEX IF NOT EXISTS idx_adj_fecha          ON adjudicacion(fecha_adjudicacion);
CREATE INDEX IF NOT EXISTS idx_pc_categoria       ON proceso_categoria(id_categoria);

-- ── 7. Vista plana (equivale al dataset original) ─────────────────

CREATE OR REPLACE VIEW v_secop_plano AS
SELECT
    e.nit_entidad,
    e.nombre_entidad,
    e.orden_entidad,
    e.codigo_pci,
    cd_e.nombre_departamento        AS departamento_entidad,
    cd_e.nombre_ciudad              AS ciudad_entidad,
    p.id_proceso,
    p.referencia_proceso,
    p.ppi,
    p.id_portafolio,
    pr.nombre_procedimiento,
    pr.descripcion                  AS descripcion_procedimiento,
    pr.fase,
    p.precio_base,
    m.nombre_modalidad              AS modalidad_contratacion,
    m.justificacion                 AS justificacion_modalidad,
    p.duracion,
    p.unidad_duracion,
    p.numero_lotes,
    p.estado_procedimiento,
    p.id_estado_procedimiento,
    p.estado_apertura,
    p.estado_resumen,
    p.tipo_contrato,
    p.subtipo_contrato,
    p.url_proceso,
    uc.nombre_unidad                AS nombre_unidad_compradora,
    cd_u.nombre_ciudad              AS ciudad_unidad_compradora,
    fp.fecha_publicacion,
    fp.fecha_ultima_publicacion,
    fp.fecha_fase_1,
    fp.fecha_fase_2,
    fp.fecha_fase_3,
    fp.fecha_recepcion_documentos,
    fp.fecha_apertura_respuestas,
    fp.fecha_apertura_efectiva,
    mp.proveedores_invitados,
    mp.proveedores_con_invitacion,
    mp.visualizaciones,
    mp.proveedores_manifestaron,
    mp.respuestas_procedimiento,
    mp.respuestas_externas,
    mp.conteo_respuestas_ofertas,
    mp.proveedores_unicos,
    a.id_adjudicacion,
    a.adjudicado,
    a.fecha_adjudicacion,
    a.valor_total                   AS valor_total_adjudicacion,
    a.nombre_adjudicador,
    pv.codigo_proveedor,
    pv.nit_proveedor                AS nit_proveedor_adjudicado,
    pv.nombre_proveedor,
    cd_pv.nombre_departamento       AS departamento_proveedor,
    cd_pv.nombre_ciudad             AS ciudad_proveedor
FROM proceso p
LEFT JOIN entidad                e     ON p.id_entidad       = e.id_entidad
LEFT JOIN ciudad                 cd_e  ON e.id_ciudad         = cd_e.id_ciudad
LEFT JOIN modalidad_contratacion m     ON p.id_modalidad     = m.id_modalidad
LEFT JOIN procedimiento          pr    ON p.id_procedimiento  = pr.id_procedimiento
LEFT JOIN unidad_compradora      uc    ON p.id_unidad         = uc.id_unidad
LEFT JOIN ciudad                 cd_u  ON uc.id_ciudad         = cd_u.id_ciudad
LEFT JOIN fase_publicacion       fp    ON p.id_proceso         = fp.id_proceso
LEFT JOIN metricas_proceso       mp    ON p.id_proceso         = mp.id_proceso
LEFT JOIN adjudicacion           a     ON p.id_proceso         = a.id_proceso
LEFT JOIN proveedor              pv    ON a.id_proveedor       = pv.id_proveedor
LEFT JOIN ciudad                 cd_pv ON pv.id_ciudad         = cd_pv.id_ciudad;


-- ── 8. Tablas Adicionales para Ingesta (Épica 1) ─────────────────

CREATE TABLE IF NOT EXISTS fuentes_datos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    endpoint TEXT,
    frecuencia_dias INT DEFAULT 1,
    estado VARCHAR(50) DEFAULT 'activa',
    ultima_sincronizacion TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS datos_crudos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fuente_id UUID NOT NULL,
    hash_registro VARCHAR(64) UNIQUE NOT NULL,
    datos_json JSONB NOT NULL,
    fecha_carga TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_datos_fuente FOREIGN KEY (fuente_id)
        REFERENCES fuentes_datos(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS logs_sincronizacion (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fuente_id UUID NOT NULL,
    fecha TIMESTAMPTZ DEFAULT NOW(),
    estado VARCHAR(50) NOT NULL,
    cantidad_registros INT DEFAULT 0,
    mensaje TEXT,
    CONSTRAINT fk_logs_fuente FOREIGN KEY (fuente_id)
        REFERENCES fuentes_datos(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_datos_crudos_fuente_id ON datos_crudos(fuente_id);
CREATE INDEX IF NOT EXISTS idx_logs_sync_fuente_id ON logs_sincronizacion(fuente_id);

