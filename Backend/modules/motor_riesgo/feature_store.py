"""PostgreSQL snapshot extraction; the durable worker pins the connection."""
from pathlib import Path
import json
import hashlib
from collections import Counter
from sqlalchemy import text
from .domain import STAGES
from .feature_builder import build_observation, capture_stage
from .history import prepare_context
from .method_reference import CONTEXT_POLICY
from .annual_context import POLICY as ANNUAL_POLICY
from analytics_ml.streams import binary_stream, physical_sha256


def fetch_batch(db, source_ids: list[int], cursor: int):
    return db.execute(text('''WITH batch AS MATERIALIZED (
            SELECT r.* FROM risk_capture_rows r WHERE r.id>:cursor AND r.fuente_id=ANY(:sources)
            ORDER BY r.id LIMIT 1000)
            SELECT r.id,r.fuente_id,r.socrata_row_id,r.id_del_proceso,r.id_adjudicacion,
        r.codigo_principal_de_categoria,r.modalidad_de_contratacion,r.departamento_entidad,
        r.precio_base,r.valor_total_adjudicacion,r.adjudicado,r.duracion,r.unidad_de_duracion,r.justificaci_n_modalidad_de,
        r.sincronizado_en,r.normalized_id,r.nit_proveedor_clave,r.nit_entidad,r.raw_buyer_key,
        r.urlproceso,r.fecha_de_publicacion_del,r.fecha_adjudicacion,r.fase,r.estado_del_procedimiento,
        CASE WHEN annual.bad_pub=0 THEN annual.pub_n END AS buyer_previous,
        CASE WHEN annual.bad_market=0 AND annual.market_n>0 THEN annual.maximum::numeric/annual.market_n END AS concentration,
        annual.bad_market=0 AND annual.market_n>0 AS market_complete,annual.market_n AS market_processes,
        annual.bad_pub AS annual_bad_pub,annual.bad_market AS annual_bad_market,annual.maximum AS annual_maximum,
        CAST(:annual_policy AS text) AS annual_policy,
        CASE WHEN COALESCE(dc.bad30,0)-COALESCE(dm.bad_date,0)-COALESCE(dm.bad_identity30,0)-COALESCE(dm.bad_category,0)=0
             THEN COALESCE(sc.n30,0)-CAST(COALESCE(sm.own_repeat,FALSE) AS integer) END AS repeated,
        CASE WHEN COALESCE(dc.bad90,0)-COALESCE(dm.bad_date,0)-COALESCE(dm.bad_identity90,0)-COALESCE(dm.bad_method,0)=0
             THEN COALESCE(dc.direct90,0)-CAST(COALESCE(dm.own_direct,FALSE) AS integer) END AS direct90,
        COALESCE(dc.bad30,0)-COALESCE(dm.bad_date,0)-COALESCE(dm.bad_identity30,0)-COALESCE(dm.bad_category,0) AS rolling_bad30,
        COALESCE(dc.bad90,0)-COALESCE(dm.bad_date,0)-COALESCE(dm.bad_identity90,0)-COALESCE(dm.bad_method,0) AS rolling_bad90,
        COALESCE(sc.n30,0)-CAST(COALESCE(sm.own_repeat,FALSE) AS integer) AS rolling_observed_repeat,
        COALESCE(dc.direct90,0)-CAST(COALESCE(dm.own_direct,FALSE) AS integer) AS rolling_observed_direct,
        CAST(:rolling_policy AS text) AS rolling_policy,u.unit_rows
        FROM batch r
        LEFT JOIN risk_row_units u ON u.id=r.id
        LEFT JOIN risk_buyer_context bc ON bc.buyer=trim(r.nit_entidad)
        LEFT JOIN risk_annual_processes ap ON ap.buyer=trim(r.nit_entidad) AND ap.source=r.fuente_id AND ap.process=trim(r.id_del_proceso)
        LEFT JOIN risk_annual_process_leaders al ON al.buyer=trim(r.nit_entidad) AND al.source=r.fuente_id AND al.process=trim(r.id_del_proceso)
        CROSS JOIN LATERAL (SELECT
            COALESCE(bc.n365,0)-CAST(COALESCE(ap.own_pub,FALSE) AS integer) AS pub_n,
            COALESCE(bc.market_processes,0)-CAST(COALESCE(ap.own_market,FALSE) AS integer) AS market_n,
            COALESCE(bc.bad_pub,0)-COALESCE(ap.bad_pub,0) AS bad_pub,
            COALESCE(bc.bad_market,0)-COALESCE(ap.bad_market,0) AS bad_market,
            COALESCE(bc.maximum,0)-CAST(COALESCE(bc.leaders,0)>0 AND COALESCE(al.n,0)=bc.leaders AS integer) AS maximum) annual
        LEFT JOIN risk_supplier_context sc ON sc.buyer=trim(r.nit_entidad) AND sc.supplier=trim(r.nit_proveedor_clave)
             AND sc.category=NULLIF(TRIM(r.codigo_principal_de_categoria),'')
        LEFT JOIN risk_supplier_direct_context dc ON dc.buyer=trim(r.nit_entidad) AND dc.supplier=trim(r.nit_proveedor_clave)
        LEFT JOIN risk_supplier_memberships sm ON sm.buyer=trim(r.nit_entidad) AND sm.supplier=trim(r.nit_proveedor_clave)
             AND sm.category=NULLIF(TRIM(r.codigo_principal_de_categoria),'') AND sm.source=r.fuente_id AND sm.process=trim(r.id_del_proceso)
        LEFT JOIN risk_direct_memberships dm ON dm.buyer=trim(r.nit_entidad) AND dm.supplier=trim(r.nit_proveedor_clave)
             AND dm.source=r.fuente_id AND dm.process=trim(r.id_del_proceso)
        ORDER BY r.id'''),
        {'cursor': cursor, 'sources': source_ids, 'rolling_policy': CONTEXT_POLICY, 'annual_policy': ANNUAL_POLICY}).mappings().all()


def fetch_stage_batch(db, source_ids: list[int], cursor: int):
    """Read only current identity/basic fields; historical predictors come from
    the reviewed registry. No population-wide NOW contexts are needed to abstain.
    """
    return db.execute(text('''WITH batch AS MATERIALIZED (
        SELECT r.id,r.fuente_id,r.socrata_row_id,r.id_del_proceso,r.id_adjudicacion,
            r.codigo_principal_de_categoria,r.modalidad_de_contratacion,r.departamento_entidad,
            r.precio_base,r.valor_total_adjudicacion,r.adjudicado,r.duracion,r.unidad_de_duracion,
            r.justificaci_n_modalidad_de,r.sincronizado_en,r.urlproceso,r.fecha_de_publicacion_del,
            r.fecha_adjudicacion,r.fase,r.estado_del_procedimiento
        FROM public.raw_secop r WHERE r.id>:cursor AND r.fuente_id=ANY(:sources)
        ORDER BY r.id LIMIT 1000)
        SELECT r.*,cp.id AS normalized_id,cp.nit_proveedor_clave,cp.nit_entidad
        FROM batch r LEFT JOIN LATERAL (
            SELECT c.id,c.nit_proveedor_clave,c.nit_entidad FROM public.contratos_procesados c
            WHERE c.raw_secop_id=r.id LIMIT 1) cp ON TRUE ORDER BY r.id'''),
        {'cursor':cursor,'sources':source_ids}).mappings().all()


def export_observations(db, target: Path, source_ids: list[int], at: str, *, include_current_context=False):
    """Stream source snapshots. These are observations NOW, never historic reconstructions.

    Bidder/deadline metrics remain absent until their source semantics are verified.
    Daily capture uses reviewed stage evidence. Computing current rolling
    contexts is an explicit diagnostic/reference operation, never backdating.
    """
    counts = {s: 0 for s in STAGES}
    cursor = 0
    if include_current_context:
        source_rows = prepare_context(db, source_ids, at)
    else:
        # Count the selected source population during the complete keyset
        # traversal. A preliminary COUNT can visit the wide heap again when
        # visibility-map coverage is low. The caller fences the capture with
        # transactional source revisions; no concurrent change can be published.
        source_rows = None
    coverage = {'source_rows': source_rows,
                'raw_rows_read': 0, 'normalized_rows_read': 0, 'observed_rows': 0,
                'capture_mode':'diagnostic_current_context' if include_current_context else 'reviewed_stage_evidence'}
    if include_current_context:
        coverage['rolling_policy'] = CONTEXT_POLICY
        coverage['rolling_universe'] = 'known_normalized_pairs_in_selected_source_capture'
        coverage['rolling_anchor'] = 'capture_at_not_historical_award_time'
        coverage['outside_universe_coverage_verified'] = False
        coverage['annual_policy'] = ANNUAL_POLICY
        coverage['annual_metric'] = 'maximum_supplier_process_participation_not_monetary_share_or_hhi'
    exclusions = Counter()
    from .stage_evidence import reviewed_stage_observations
    from .service import managed_path
    checksum = hashlib.sha256()
    with binary_stream(target, 'wb') as out:
        while True:
            rows = (fetch_batch if include_current_context else fetch_stage_batch)(db, source_ids, cursor)
            if not rows:
                break
            reviewed,review_failures=reviewed_stage_observations(db,rows,at,managed_path('evidence'))
            for row in rows:
                cursor = row['id']
                coverage['raw_rows_read'] += 1
                if row['normalized_id'] is None:
                    continue
                coverage['normalized_rows_read'] += 1
                observation = build_observation(row, at)
                if observation is None:
                    exclusions[capture_stage(row, at)[1]] += 1
                    continue
                current_stage=observation['stage']
                stages=['CONVOCATORIA','ADJUDICACION'] if current_stage=='ADJUDICACION' else ['CONVOCATORIA']
                for stage in stages:
                    key=(row['id'],stage)
                    historical=reviewed.get(key)
                    if historical is None and stage!=current_stage:
                        if key in review_failures:exclusions[review_failures[key]]+=1
                        continue
                    item=historical or observation
                    if key in review_failures:
                        item={**item,'capture_reasons':[*item.get('capture_reasons',[]),review_failures[key]]}
                    encoded = (json.dumps(item, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n').encode('utf-8')
                    out.write(encoded)
                    checksum.update(encoded)
                    counts[item['stage']] += 1
                    coverage['observed_rows'] += 1
            db.commit()  # bound transaction age; source signature is checked before publication
    if source_rows is None:
        coverage['source_rows'] = coverage['raw_rows_read']
        coverage['source_count_scope'] = 'complete_selected_source_keyset_traversal'
    coverage['not_normalized_rows'] = max(0, coverage['source_rows'] - coverage['normalized_rows_read'])
    coverage['exclusions'] = dict(exclusions)
    coverage['stage_counts'] = counts
    coverage['observations_sha256'] = checksum.hexdigest()
    coverage['hash_scope'] = 'uncompressed_jsonl_bytes'
    coverage['file_sha256'] = physical_sha256(target)
    coverage['file_bytes'] = target.stat().st_size
    coverage['encoding'] = 'gzip' if target.name.endswith('.gz') else 'jsonl'
    target.with_suffix('.coverage.json').write_text(json.dumps(coverage, ensure_ascii=False), encoding='utf-8')
    return counts

