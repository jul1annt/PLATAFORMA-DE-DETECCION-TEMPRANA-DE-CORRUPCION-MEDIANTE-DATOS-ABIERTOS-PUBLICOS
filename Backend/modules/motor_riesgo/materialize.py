"""Build a narrow, ordered capture once; public rows are never rewritten."""
from sqlalchemy import text


FIELDS = '''r.id,r.fuente_id,r.socrata_row_id,r.id_del_proceso,r.id_adjudicacion,r.nit_entidad AS raw_buyer_key,
    r.codigo_principal_de_categoria,r.modalidad_de_contratacion,r.departamento_entidad,
    r.precio_base,r.valor_total_adjudicacion,r.adjudicado,r.duracion,r.unidad_de_duracion,
    r.justificaci_n_modalidad_de,r.sincronizado_en,r.urlproceso,r.fecha_de_publicacion_del,
    r.fecha_adjudicacion,r.fase,r.estado_del_procedimiento,cp.id AS normalized_id,
    cp.nit_proveedor_clave,cp.nit_entidad,cp.modalidad_contratacion AS normalized_modality'''


def prepare_capture(db, source_ids: list[int]) -> int:
    for name in ('risk_capture_rows', 'risk_capture_base', 'risk_row_units'):
        db.execute(text('DROP TABLE IF EXISTS pg_temp.' + name))
    db.execute(text('CREATE TEMP TABLE risk_capture_base AS SELECT ' + FIELDS + '''
        FROM raw_secop r LEFT JOIN contratos_procesados cp ON cp.raw_secop_id=r.id WHERE FALSE'''))
    cursor = 0
    captured = 0
    while True:
        wanted, end = db.execute(text('''SELECT count(*),max(id) FROM (
            SELECT id FROM raw_secop WHERE id>:cursor AND fuente_id=ANY(:sources)
            ORDER BY id LIMIT 100000) ids'''), {'cursor': cursor, 'sources': source_ids}).one()
        if not wanted:
            break
        # Bound BOTH sides. A merge against the entire normalized index can
        # otherwise restart from its beginning for every advancing cursor.
        result = db.execute(text('INSERT INTO pg_temp.risk_capture_base SELECT ' + FIELDS + '''
            FROM raw_secop r LEFT JOIN (
                SELECT id,raw_secop_id,nit_proveedor_clave,nit_entidad,modalidad_contratacion
                FROM contratos_procesados WHERE raw_secop_id>:cursor AND raw_secop_id<=:end OFFSET 0
            ) cp ON cp.raw_secop_id=r.id
            WHERE r.id>:cursor AND r.id<=:end AND r.fuente_id=ANY(:sources)
            ORDER BY r.id'''), {'cursor': cursor, 'end': end, 'sources': source_ids})
        if result.rowcount != wanted:
            raise ValueError('La proyección no conserva una fila por registro de la fuente')
        captured += wanted
        cursor = end
    # Sort only IDs and counts. Sorting every wide payload twice exceeded the
    # resource budget on the real copy. The base heap is already ordered by ID.
    db.execute(text('''CREATE TEMP TABLE risk_row_units AS
        SELECT id,count(*) OVER(PARTITION BY fuente_id,NULLIF(trim(id_del_proceso),''),
            CASE WHEN upper(trim(adjudicado)) IN ('SI','SÍ','TRUE','1')
                 THEN COALESCE(NULLIF(trim(id_adjudicacion),''),'') ELSE '' END) AS unit_rows
        FROM risk_capture_base b ORDER BY id'''))
    db.execute(text('CREATE UNIQUE INDEX ON risk_row_units(id)'))
    db.execute(text('ANALYZE pg_temp.risk_row_units'))
    db.execute(text('ALTER TABLE pg_temp.risk_capture_base RENAME TO risk_capture_rows'))
    db.execute(text('CREATE UNIQUE INDEX ON risk_capture_rows(id)'))
    db.execute(text('ANALYZE pg_temp.risk_capture_rows'))
    return captured
