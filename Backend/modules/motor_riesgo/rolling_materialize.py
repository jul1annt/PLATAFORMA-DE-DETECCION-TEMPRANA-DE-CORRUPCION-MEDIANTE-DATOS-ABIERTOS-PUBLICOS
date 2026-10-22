"""Aggregate strict counts once per capture, pair, category and official process.

No per-contract history scan. Unknown quality is retained per process so excluding
the target process also excludes its quality failures. The universe is explicitly
the known normalized pairs in the selected sources, not all national procurement.
"""
from sqlalchemy import text
from .method_reference import DIRECT, OTHER

MISSING = ['', 'N/A', 'NA', 'NULL', 'NONE', 'NO DEFINIDO', 'NO ADJUDICADO', 'SIN DATO', 'NO APLICA']
TABLES = ('risk_rolling_rows', 'risk_supplier_memberships', 'risk_supplier_context',
          'risk_direct_memberships', 'risk_supplier_direct_context')


def prepare_rolling_context(db, at):
    for table in reversed(TABLES):
        db.execute(text('DROP TABLE IF EXISTS pg_temp.' + table))
    params = {'at': at, 'missing': MISSING, 'pair_missing': MISSING + ['0', '-'],
              'direct_methods': sorted(DIRECT), 'other_methods': sorted(OTHER)}
    db.execute(text(r'''CREATE TEMP TABLE risk_rolling_rows AS
        WITH cleaned AS (
            SELECT r.fuente_id AS source,
                CASE WHEN upper(trim(COALESCE(r.id_del_proceso,'')))=ANY(:missing) THEN NULL ELSE trim(r.id_del_proceso) END AS process,
                CASE WHEN upper(trim(COALESCE(r.id_adjudicacion,'')))=ANY(:missing) THEN NULL ELSE trim(r.id_adjudicacion) END AS award,
                CASE WHEN upper(trim(COALESCE(r.socrata_row_id,'')))=ANY(:missing) THEN NULL ELSE trim(r.socrata_row_id) END AS row_id,
                CASE WHEN upper(trim(COALESCE(r.nit_entidad,'')))=ANY(:pair_missing) THEN NULL ELSE trim(r.nit_entidad) END AS buyer,
                CASE WHEN upper(trim(COALESCE(r.nit_proveedor_clave,'')))=ANY(:pair_missing) THEN NULL ELSE trim(r.nit_proveedor_clave) END AS supplier,
                CASE WHEN upper(trim(COALESCE(r.codigo_principal_de_categoria,'')))=ANY(:missing) THEN NULL ELSE trim(r.codigo_principal_de_categoria) END AS category,
                r.fecha_adjudicacion AS awarded_at,u.unit_rows,
                upper(trim(COALESCE(r.adjudicado,''))) AS status,
                trim(regexp_replace(upper(regexp_replace(normalize(COALESCE(r.modalidad_de_contratacion,''),NFKD),
                    '['||chr(768)||'-'||chr(879)||']','','g')),'[[:space:]]+',' ','g')) AS method
            FROM risk_capture_rows r LEFT JOIN risk_row_units u ON u.id=r.id
            WHERE (r.fecha_de_publicacion_del IS NULL OR r.fecha_de_publicacion_del<=CAST(:at AS timestamptz))
              AND upper(trim(COALESCE(r.adjudicado,''))) NOT IN ('NO','FALSE','0')
              AND (r.fecha_adjudicacion IS NULL OR r.fecha_adjudicacion BETWEEN
                   CAST(:at AS timestamptz)-INTERVAL '2160 hours' AND CAST(:at AS timestamptz))
        )
        SELECT *, COALESCE(unit_rows=1 AND process IS NOT NULL AND award IS NOT NULL AND row_id IS NOT NULL
                           AND status IN ('SI','SÍ','TRUE','1'),FALSE) AS valid,
               CASE WHEN method=ANY(:direct_methods) THEN TRUE WHEN method=ANY(:other_methods) THEN FALSE END AS direct
        FROM cleaned WHERE buyer IS NOT NULL AND supplier IS NOT NULL'''), params)
    db.execute(text('CREATE INDEX ON risk_rolling_rows(buyer,supplier,source,process)'))
    db.execute(text('''CREATE TEMP TABLE risk_direct_memberships AS
        SELECT buyer,supplier,source,process,
            bool_or(valid AND awarded_at IS NOT NULL AND direct IS TRUE) AS own_direct,
            count(*) FILTER(WHERE awarded_at IS NULL) AS bad_date,
            count(*) FILTER(WHERE awarded_at IS NOT NULL AND NOT valid) AS bad_identity90,
            count(*) FILTER(WHERE awarded_at>=CAST(:at AS timestamptz)-INTERVAL '720 hours' AND NOT valid) AS bad_identity30,
            count(*) FILTER(WHERE valid AND awarded_at IS NOT NULL AND direct IS NULL) AS bad_method,
            count(*) FILTER(WHERE valid AND awarded_at>=CAST(:at AS timestamptz)-INTERVAL '720 hours' AND category IS NULL) AS bad_category
        FROM risk_rolling_rows GROUP BY buyer,supplier,source,process'''), params)
    db.execute(text('CREATE UNIQUE INDEX ON risk_direct_memberships(buyer,supplier,source,process)'))
    db.execute(text('''CREATE TEMP TABLE risk_supplier_direct_context AS
        SELECT buyer,supplier,count(*) FILTER(WHERE own_direct) AS direct90,
            sum(bad_date+bad_identity90+bad_method) AS bad90,
            sum(bad_date+bad_identity30+bad_category) AS bad30,
            sum(bad_date) AS bad_date,sum(bad_identity90) AS bad_identity90,
            sum(bad_identity30) AS bad_identity30,sum(bad_method) AS bad_method,sum(bad_category) AS bad_category
        FROM risk_direct_memberships GROUP BY buyer,supplier'''))
    db.execute(text('CREATE UNIQUE INDEX ON risk_supplier_direct_context(buyer,supplier)'))
    db.execute(text('''CREATE TEMP TABLE risk_supplier_memberships AS
        SELECT buyer,supplier,category,source,process,TRUE AS own_repeat FROM risk_rolling_rows
        WHERE valid AND category IS NOT NULL AND awarded_at>=CAST(:at AS timestamptz)-INTERVAL '720 hours'
        GROUP BY buyer,supplier,category,source,process'''), params)
    db.execute(text('CREATE UNIQUE INDEX ON risk_supplier_memberships(buyer,supplier,category,source,process)'))
    db.execute(text('''CREATE TEMP TABLE risk_supplier_context AS
        SELECT buyer,supplier,category,count(*) AS n30 FROM risk_supplier_memberships GROUP BY buyer,supplier,category'''))
    db.execute(text('CREATE UNIQUE INDEX ON risk_supplier_context(buyer,supplier,category)'))
    for table in TABLES:
        db.execute(text('ANALYZE pg_temp.' + table))
