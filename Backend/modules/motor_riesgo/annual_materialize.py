"""Indexed annual aggregates with per-process quality and exact target removal."""
from sqlalchemy import text
from .rolling_materialize import MISSING

TABLES = ('risk_annual_rows','risk_annual_processes','risk_annual_suppliers',
          'risk_annual_supplier_counts','risk_buyer_context','risk_annual_process_leaders')


def prepare_annual_context(db, at):
    for table in reversed(TABLES): db.execute(text('DROP TABLE IF EXISTS pg_temp.'+table))
    params={'at':at,'missing':MISSING,'pair_missing':MISSING+['0','-']}
    db.execute(text('''CREATE TEMP TABLE risk_annual_rows AS
        WITH cleaned AS (SELECT r.fuente_id AS source,
            CASE WHEN upper(trim(COALESCE(r.nit_entidad,'')))=ANY(:pair_missing) THEN NULL ELSE trim(r.nit_entidad) END AS normalized_buyer,
            CASE WHEN upper(trim(COALESCE(r.raw_buyer_key,'')))=ANY(:pair_missing) THEN NULL ELSE trim(r.raw_buyer_key) END AS raw_buyer,
            CASE WHEN upper(trim(COALESCE(r.id_del_proceso,'')))=ANY(:missing) THEN NULL ELSE trim(r.id_del_proceso) END AS process,
            CASE WHEN upper(trim(COALESCE(r.id_adjudicacion,'')))=ANY(:missing) THEN NULL ELSE trim(r.id_adjudicacion) END AS award,
            CASE WHEN upper(trim(COALESCE(r.socrata_row_id,'')))=ANY(:missing) THEN NULL ELSE trim(r.socrata_row_id) END AS row_id,
            CASE WHEN upper(trim(COALESCE(r.nit_proveedor_clave,'')))=ANY(:pair_missing) THEN NULL ELSE trim(r.nit_proveedor_clave) END AS supplier,
            CASE WHEN isfinite(r.fecha_de_publicacion_del) THEN r.fecha_de_publicacion_del END AS published_at,
            CASE WHEN isfinite(r.fecha_adjudicacion) THEN r.fecha_adjudicacion END AS awarded_at,
            upper(trim(COALESCE(r.adjudicado,''))) AS status,u.unit_rows
            FROM risk_capture_rows r LEFT JOIN risk_row_units u ON u.id=r.id
            WHERE (r.fecha_de_publicacion_del IS NULL OR NOT isfinite(r.fecha_de_publicacion_del)
                   OR r.fecha_de_publicacion_del<=CAST(:at AS timestamptz))
              AND (r.fecha_de_publicacion_del IS NULL OR NOT isfinite(r.fecha_de_publicacion_del)
                   OR r.fecha_de_publicacion_del>=CAST(:at AS timestamptz)-INTERVAL '8760 hours'
                   OR (upper(trim(COALESCE(r.adjudicado,''))) NOT IN ('NO','FALSE','0') AND
                       (r.fecha_adjudicacion IS NULL OR NOT isfinite(r.fecha_adjudicacion) OR
                        r.fecha_adjudicacion BETWEEN CAST(:at AS timestamptz)-INTERVAL '8760 hours' AND CAST(:at AS timestamptz))))),
        expanded AS (SELECT *,COALESCE(normalized_buyer,raw_buyer) AS buyer,
            normalized_buyer IS NOT NULL AND (raw_buyer IS NULL OR raw_buyer=normalized_buyer) AS normalized_ok FROM cleaned
            UNION ALL SELECT *,raw_buyer AS buyer,FALSE AS normalized_ok FROM cleaned
            WHERE raw_buyer IS NOT NULL AND normalized_buyer IS NOT NULL AND raw_buyer<>normalized_buyer)
        SELECT *,source>0 AND process IS NOT NULL AND row_id IS NOT NULL AND normalized_ok AS process_ok
        FROM expanded WHERE buyer IS NOT NULL AND (published_at IS NULL OR published_at<=CAST(:at AS timestamptz))'''),params)
    db.execute(text('CREATE INDEX ON risk_annual_rows(buyer,source,process)'))
    db.execute(text('''CREATE TEMP TABLE risk_annual_processes AS
        SELECT buyer,source,process,
            bool_or(process IS NOT NULL AND published_at BETWEEN CAST(:at AS timestamptz)-INTERVAL '8760 hours' AND CAST(:at AS timestamptz)) AS own_pub,
            count(*) FILTER(WHERE published_at IS NULL OR
                (published_at>=CAST(:at AS timestamptz)-INTERVAL '8760 hours' AND NOT process_ok)) AS bad_pub,
            bool_or(process IS NOT NULL AND status NOT IN ('NO','FALSE','0') AND
                awarded_at BETWEEN CAST(:at AS timestamptz)-INTERVAL '8760 hours' AND CAST(:at AS timestamptz)) AS own_market,
            count(*) FILTER(WHERE status NOT IN ('NO','FALSE','0') AND (awarded_at IS NULL OR
                (awarded_at BETWEEN CAST(:at AS timestamptz)-INTERVAL '8760 hours' AND CAST(:at AS timestamptz)
                 AND NOT COALESCE(process_ok AND unit_rows=1 AND award IS NOT NULL AND supplier IS NOT NULL
                                  AND status IN ('SI','SÍ','TRUE','1'),FALSE)))) AS bad_market
        FROM risk_annual_rows GROUP BY buyer,source,process'''),params)
    db.execute(text('CREATE UNIQUE INDEX ON risk_annual_processes(buyer,source,process)'))
    db.execute(text('''CREATE TEMP TABLE risk_annual_suppliers AS
        SELECT DISTINCT buyer,supplier,source,process FROM risk_annual_rows
        WHERE process_ok AND unit_rows=1 AND award IS NOT NULL AND supplier IS NOT NULL
            AND status IN ('SI','SÍ','TRUE','1')
            AND awarded_at BETWEEN CAST(:at AS timestamptz)-INTERVAL '8760 hours' AND CAST(:at AS timestamptz)'''),params)
    db.execute(text('CREATE UNIQUE INDEX ON risk_annual_suppliers(buyer,supplier,source,process)'))
    db.execute(text('''CREATE TEMP TABLE risk_annual_supplier_counts AS
        SELECT buyer,supplier,count(*) AS n FROM risk_annual_suppliers GROUP BY buyer,supplier'''))
    db.execute(text('CREATE UNIQUE INDEX ON risk_annual_supplier_counts(buyer,supplier)'))
    db.execute(text('''CREATE TEMP TABLE risk_buyer_context AS
        WITH counts AS (SELECT buyer,count(*) FILTER(WHERE own_pub) AS n365,sum(bad_pub) AS bad_pub,
            count(*) FILTER(WHERE own_market) AS market_processes,sum(bad_market) AS bad_market
            FROM risk_annual_processes GROUP BY buyer),
        maxima AS (SELECT buyer,max(n) AS maximum FROM risk_annual_supplier_counts GROUP BY buyer),
        leaders AS (SELECT s.buyer,count(*) AS leaders FROM risk_annual_supplier_counts s JOIN maxima m
            ON m.buyer=s.buyer AND m.maximum=s.n GROUP BY s.buyer)
        SELECT c.*,COALESCE(m.maximum,0) AS maximum,COALESCE(l.leaders,0) AS leaders
        FROM counts c LEFT JOIN maxima m USING(buyer) LEFT JOIN leaders l USING(buyer)'''))
    db.execute(text('CREATE UNIQUE INDEX ON risk_buyer_context(buyer)'))
    db.execute(text('''CREATE TEMP TABLE risk_annual_process_leaders AS
        SELECT p.buyer,p.source,p.process,count(*) AS n FROM risk_annual_suppliers p
        JOIN risk_annual_supplier_counts s USING(buyer,supplier)
        JOIN risk_buyer_context b ON b.buyer=s.buyer AND b.maximum=s.n
        GROUP BY p.buyer,p.source,p.process'''))
    db.execute(text('CREATE UNIQUE INDEX ON risk_annual_process_leaders(buyer,source,process)'))
    for table in TABLES: db.execute(text('ANALYZE pg_temp.'+table))
