-- ── 9. Tablas Adicionales para Procesamiento y Calidad (Épica 2) ─────────────────

CREATE TABLE IF NOT EXISTS contratos_procesados (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_proceso VARCHAR(100) NOT NULL,
    entidad TEXT,
    proveedor TEXT,
    valor NUMERIC(20,2),
    fecha DATE,
    tipo_contrato TEXT,
    fuente_id UUID NOT NULL,
    fecha_carga TIMESTAMPTZ DEFAULT NOW(),
    hash_procesado VARCHAR(64) UNIQUE NOT NULL,
    estado_calidad VARCHAR(20) NOT NULL DEFAULT 'OK',
    CONSTRAINT fk_cp_fuente FOREIGN KEY (fuente_id)
        REFERENCES fuentes_datos(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS calidad_datos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contrato_id UUID NOT NULL,
    tipo_problema VARCHAR(50) NOT NULL,
    campo VARCHAR(100),
    descripcion TEXT,
    fecha TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_calidad_contrato FOREIGN KEY (contrato_id)
        REFERENCES contratos_procesados(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS resumen_calidad (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fuente_id UUID NOT NULL,
    total_registros INT DEFAULT 0,
    incompletos INT DEFAULT 0,
    sospechosos INT DEFAULT 0,
    fecha TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_resumen_fuente FOREIGN KEY (fuente_id)
        REFERENCES fuentes_datos(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cambios_contratos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_proceso VARCHAR(100) NOT NULL,
    campo VARCHAR(100) NOT NULL,
    valor_anterior TEXT,
    valor_nuevo TEXT,
    fecha TIMESTAMPTZ DEFAULT NOW()
);

-- Índices (Bonus Épica 2)
CREATE INDEX IF NOT EXISTS idx_cp_fecha ON contratos_procesados(fecha);
CREATE INDEX IF NOT EXISTS idx_cp_proveedor ON contratos_procesados(proveedor);
CREATE INDEX IF NOT EXISTS idx_cp_valor ON contratos_procesados(valor);
CREATE INDEX IF NOT EXISTS idx_cp_id_proceso ON contratos_procesados(id_proceso);
CREATE INDEX IF NOT EXISTS idx_cp_estado_calidad ON contratos_procesados(estado_calidad);
CREATE INDEX IF NOT EXISTS idx_cambios_id_proceso ON cambios_contratos(id_proceso);
