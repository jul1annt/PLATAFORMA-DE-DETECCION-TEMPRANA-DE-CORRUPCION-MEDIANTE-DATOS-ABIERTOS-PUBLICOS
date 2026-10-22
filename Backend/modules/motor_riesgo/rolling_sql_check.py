"""Independent PostgreSQL count/quality comparator for the offline reference.

Only SELECT over the supplied JSON frame. This is a validation tool, not the
legacy history materializer or a population extractor. Typed monetary parsing is
shared; currency aggregation is independent. No original denomination is inferred.
SQLAlchemy remains outside the pure domain and ML environments.
"""
import json
from datetime import timedelta
from sqlalchemy import text
from .domain import canonical, instant, official_id, digest
from .rolling_evidence import assess, monetary_value


SQL = '''WITH raw AS (
    SELECT * FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS x(
        source numeric, process text, award text, at timestamptz,
        verified boolean, method_verified boolean, direct boolean,
        category text, method text, fingerprint text, amount numeric, currency text)
), other AS (
    SELECT * FROM raw WHERE NOT (source IS NOT DISTINCT FROM CAST(:source AS numeric)
        AND process IS NOT DISTINCT FROM CAST(:process AS text))
), window_rows AS (
    SELECT *, source>0 AND process IS NOT NULL AND award IS NOT NULL AND verified IS TRUE AS valid
    FROM other WHERE at BETWEEN CAST(:at AS timestamptz)-INTERVAL '2160 hours' AND CAST(:at AS timestamptz)
), units AS (
    SELECT source,process,award,min(at) AS at,
        bool_or(at>=CAST(:at AS timestamptz)-INTERVAL '720 hours') AS in30,
        count(DISTINCT fingerprint) AS versions,
        bool_and(method_verified AND direct IS NOT NULL AND method IS NOT NULL) AS method_known,
        bool_and(direct) AS direct, min(category) AS category,
        min(amount) AS amount,min(currency) AS currency
    FROM window_rows WHERE valid IS TRUE GROUP BY source,process,award
), selected_direct AS (
    SELECT * FROM units WHERE versions=1 AND method_known AND direct
), selected_repeat AS (
    SELECT * FROM units WHERE versions=1 AND in30 AND category=CAST(:category AS text)
), reason_rows AS (
    SELECT 'directas_90d' AS field,'historia_incompleta' AS reason,CASE WHEN :complete90 THEN 0 ELSE 1 END::bigint AS n
    UNION ALL SELECT 'reiteraciones_30d','historia_incompleta',CASE WHEN :complete30 THEN 0 ELSE 1 END
    UNION ALL SELECT 'reiteraciones_30d','categoria_objetivo_ausente',CASE WHEN CAST(:category AS text) IS NULL THEN 1 ELSE 0 END
    UNION ALL SELECT 'directas_90d','fecha_adjudicacion_invalida',count(*) FROM other WHERE at IS NULL
    UNION ALL SELECT 'reiteraciones_30d','fecha_adjudicacion_invalida',count(*) FROM other WHERE at IS NULL
    UNION ALL SELECT 'directas_90d','identidad_no_comprobada',count(*) FROM window_rows WHERE valid IS NOT TRUE
    UNION ALL SELECT 'reiteraciones_30d','identidad_no_comprobada',count(*) FROM window_rows
        WHERE valid IS NOT TRUE AND at>=CAST(:at AS timestamptz)-INTERVAL '720 hours'
    UNION ALL SELECT 'directas_90d','versiones_contradictorias',count(*) FROM units WHERE versions>1
    UNION ALL SELECT 'reiteraciones_30d','versiones_contradictorias',count(*) FROM units WHERE versions>1 AND in30
    UNION ALL SELECT 'directas_90d','modalidad_no_verificada',count(*) FROM units WHERE versions=1 AND method_known IS NOT TRUE
    UNION ALL SELECT 'reiteraciones_30d','categoria_ausente',count(*) FROM units WHERE versions=1 AND in30 AND category IS NULL
), reasons AS (
    SELECT field,jsonb_object_agg(reason,n) AS reasons FROM reason_rows WHERE n>0 GROUP BY field
), counts AS (
    SELECT 'directas_90d' AS field,count(DISTINCT (source,process)) AS processes,count(*) AS awards FROM selected_direct
    UNION ALL SELECT 'reiteraciones_30d',count(DISTINCT (source,process)),count(*) FROM selected_repeat
), money_rows AS (
    SELECT 'directas_90d' AS field,amount,currency FROM selected_direct
    UNION ALL SELECT 'reiteraciones_30d',amount,currency FROM selected_repeat
), money_totals AS (
    SELECT field,currency,sum(amount) AS total FROM money_rows
    WHERE amount IS NOT NULL AND currency IS NOT NULL GROUP BY field,currency
), money_objects AS (
    SELECT field,jsonb_object_agg(currency,total::text) AS amounts FROM money_totals GROUP BY field
), money_invalid AS (
    SELECT field,count(*) FILTER(WHERE amount IS NULL OR currency IS NULL) AS invalid FROM money_rows GROUP BY field
), ignored AS (
    SELECT 'proceso_objetivo' AS reason,(SELECT count(*) FROM raw)-(SELECT count(*) FROM other) AS n
    UNION ALL SELECT 'evento_futuro',count(*) FROM other WHERE at>CAST(:at AS timestamptz)
    UNION ALL SELECT 'fuera_de_ventana',count(*) FROM other WHERE at<CAST(:at AS timestamptz)-INTERVAL '2160 hours'
)
SELECT jsonb_build_object(
    'indicators',(SELECT jsonb_object_agg(c.field,jsonb_build_object(
        'count',CASE WHEN r.reasons IS NULL THEN c.processes END,
        'observed_distinct_processes',c.processes,'observed_awards',c.awards,
        'reasons',COALESCE(r.reasons,'{}'::jsonb),
        'amounts_by_currency',COALESCE(m.amounts,'{}'::jsonb),
        'amounts_complete',r.reasons IS NULL AND COALESCE(i.invalid,0)=0,
        'awards_without_verified_amount_currency',COALESCE(i.invalid,0)))
        FROM counts c LEFT JOIN reasons r USING(field) LEFT JOIN money_objects m USING(field)
        LEFT JOIN money_invalid i USING(field)),
    'ignored',COALESCE((SELECT jsonb_object_agg(reason,n) FROM ignored WHERE n>0),'{}'::jsonb))
'''


def compare(db, payload):
    """Validate input with the reference, independently aggregate counts in SQL."""
    reference = assess(payload)
    rows = []
    for row in payload['rows']:
        try:
            at = instant(row['award_at']).isoformat()
        except (ValueError, TypeError, KeyError, AttributeError):
            at = None
        source = row.get('source_id')
        amount, currency = monetary_value(row.get('amount'), row.get('currency'))
        rows.append({'source': source if type(source) is int else None,
                     'process': official_id(row.get('process_id')), 'award': official_id(row.get('award_id')),
                     'at': at, 'verified': row.get('identity_verified') is True,
                     'method_verified': row.get('method_semantics_verified') is True,
                     'direct': row.get('direct') if type(row.get('direct')) is bool else None,
                     'method': official_id(row.get('method')), 'category': official_id(row.get('category')),
                     'amount': str(amount) if amount is not None else None, 'currency': currency,
                     'fingerprint': canonical({field: row.get(field) for field in
                         ('award_at', 'category', 'direct', 'method_semantics_verified', 'amount', 'currency', 'method', 'justification')}).decode()})
    target = payload['target']
    at, start = instant(target['award_at']), instant(payload['scope']['start'])
    params = {'rows': json.dumps(rows, allow_nan=False), 'source': target['source_id'],
              'process': official_id(target['process_id']), 'category': official_id(target.get('category')),
              'at': reference['target']['award_at'],
              'complete90': payload['scope']['complete_pair_history'] and start <= at - timedelta(days=90),
              'complete30': payload['scope']['complete_pair_history'] and start <= at - timedelta(days=30)}
    result = db.execute(text(SQL), params).scalar_one()
    expected = {'indicators': {field: {key: value[key] for key in
                 ('count', 'observed_distinct_processes', 'observed_awards', 'reasons',
                  'amounts_by_currency', 'amounts_complete', 'awards_without_verified_amount_currency')}
                 for field, value in reference['indicators'].items()}, 'ignored': reference['ignored']}
    return {'policy': 'rolling-count-quality-money-sql-comparator-v2', 'match': result == expected,
            'reference': expected, 'sql': result, 'input_sha256': digest(payload),
            'sql_sha256': digest(SQL), 'count_and_quality_parity_only': False,
            'monetary_parity_checked': True, 'monetary_parsing_shared': True,
            'source_currency_verified': False, 'legacy_history_parity_checked': False,
            'database_writes': False, 'publication_authorized': False, 'training_eligible': False}
