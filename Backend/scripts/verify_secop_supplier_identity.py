"""Read-only full-cut supplier audit on the existing, guarded acceptance copy.

This verifies SECOP provenance/normalization, not external taxpayer identity.
No data is loaded, reprocessed, repaired or sent to an external service.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
from itertools import zip_longest
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback
from urllib.parse import urlsplit

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session


def run(root, output):
    root = root.resolve()
    output = output.resolve()
    if not output.is_relative_to(root) or output.exists():
        raise ValueError('Use a new report inside the integration directory')
    work = root / 'full-acceptance-20261011'
    preparation = json.loads((work / 'preparation.json').read_text())
    candidate = json.loads((work / 'readiness-candidate.json').read_text())
    package = Path(candidate['backend']).resolve()
    assert package.is_relative_to(root / 'releases')
    assert candidate['ref'] == '794d185832c7c56ffa4d91ef08ca1f3d15128be5'
    expected_database = 'codex_plan_full_acceptance_20261011_test'
    assert preparation['target_database'] == expected_database and preparation['target_oid'] == 75045
    assert preparation['copied_counts']['raw_secop'] == preparation['copied_counts']['contratos_procesados'] == 9249545
    values = dotenv_values(work / 'runtime.env')
    assert (values['DB_HOST'], values['DB_PORT'], values['DB_NAME'], values['DB_USER']) == ('127.0.0.1', '5433', expected_database, 'plataforma_integracion')
    code_files = ('modules/transformacion/services/normalization_service.py',
                  'modules/transformacion/services/trasformacionservice.py',
                  'modules/transformacion/repository/transformacion.py',
                  'modules/analitica/repository/repository.py')
    manifest = {item['path']: item for item in candidate['files']}
    hashes = {}
    for name in code_files:
        hashes[name] = hashlib.sha256((package / name).read_bytes()).hexdigest()
        assert hashes[name] == manifest[name]['sha256']
    os.environ.update({k: v for k, v in values.items() if v is not None})
    sys.path.insert(0, str(package))
    from modules.transformacion.services.normalization_service import normalize_provider_nit, normalize_provider_nit_identity, normalize_text
    from modules.transformacion.repository.transformacion import TransformacionRepository
    normalize_nit = lru_cache(maxsize=250000)(normalize_provider_nit)
    normalize_key = lru_cache(maxsize=250000)(normalize_provider_nit_identity)
    normalize_name = lru_cache(maxsize=250000)(normalize_text)
    engine = create_engine(URL.create('postgresql', username=values['DB_USER'], password=values['DB_PASSWORD'], host='127.0.0.1', port=5433, database=expected_database), hide_parameters=True, pool_size=1, max_overflow=0, connect_args={'connect_timeout': 15, 'application_name': 'p06_secop_readonly_audit'})
    start = time.monotonic()
    report = {'stage': 'starting', 'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'authorization': 'Sí, ajustar P06 a SECOP', 'source_scope': 'SECOP only',
              'dian_identity_contrast_performed': False, 'database_writes': 0,
              'historical_reload_performed': False, 'normalization_reprocessing_performed': False,
              'candidate_ref': candidate['ref'], 'code_sha256': hashes,
              'evaluated_raw_rows': 0, 'evaluated_processed_rows': 0,
              'mismatches': {}, 'case_references': [], 'classification': {},
              'limits': ['Internal consistency with SECOP and implemented normalization rules only; no independent confirmation of taxpayer existence, ownership or historical tax status.', 'The retained acceptance copy includes the previously documented processing/fault exercise; this audit does not claim all its derived fields are identical to the published database.', 'No identities are assigned to the 18980 pre-Socrata legacy rows; P05/P12 remain separate.']}
    binding_names = ('release.json', 'runtime.json', 'runtime.env', 'provision.json', 'frontend-build.json')
    def bindings():
        return {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in binding_names}
    initial_bindings = bindings()
    def save(stage):
        report.update(stage=stage, elapsed_seconds=round(time.monotonic() - start, 3), updated_at_utc=datetime.now(timezone.utc).isoformat())
        temporary = output.with_suffix('.partial')
        temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + '\n', encoding='utf-8')
        temporary.replace(output)
        print(json.dumps({'stage': stage, 'raw': report['evaluated_raw_rows'], 'processed': report['evaluated_processed_rows'], 'seconds': report['elapsed_seconds']}), flush=True)
    def configure(db):
        db.execute(text('SET TRANSACTION READ ONLY'))
        for setting in ("SET LOCAL TIME ZONE 'UTC'", "SET LOCAL statement_timeout='600s'", "SET LOCAL lock_timeout='1s'", "SET LOCAL idle_in_transaction_session_timeout='120s'", "SET LOCAL work_mem='32MB'", 'SET LOCAL max_parallel_workers_per_gather=0'):
            db.execute(text(setting))
        identity = tuple(db.execute(text('SELECT current_database(),inet_server_port(),current_user,(SELECT oid FROM pg_database WHERE datname=current_database()),(SELECT version_num FROM alembic_version)')).one())
        assert identity == (expected_database, 5433, 'plataforma_integracion', 75045, '3c19a8f7e2d0')
        assert db.execute(text("SELECT current_setting('transaction_read_only')")).scalar_one() == 'on'
        assert not any(db.execute(text('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname=current_user')).one())
        assert db.execute(text('SELECT count(*) FROM fuentes_datos WHERE activo')).scalar_one() == 0
        assert db.execute(text('SELECT count(*) FROM background_jobs WHERE active')).scalar_one() == 0
        assert db.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND backend_type='client backend'")).scalar_one() == 0
        return identity
    def snapshot(db):
        return {'summary': dict(db.execute(text('SELECT * FROM contratos_metricas_calidad WHERE id=1')).mappings().one()),
                'control': {t: dict(db.execute(text(f"SELECT count(*) AS rows, md5(string_agg(md5(to_jsonb(x)::text),'' ORDER BY md5(to_jsonb(x)::text))) AS fingerprint FROM {t} x")).mappings().one()) for t in ('fuentes_datos', 'background_jobs')},
                'bounded_fingerprints': {t: db.execute(text(f"SELECT md5(string_agg(md5(to_jsonb(x)::text),'' ORDER BY id)) FROM (SELECT * FROM {t} ORDER BY id LIMIT 2000) x")).scalar_one() for t in ('raw_secop', 'contratos_procesados')}}
    mismatches = Counter()
    classes = Counter()
    expected_groups = Counter()
    first_key_by_name, first_name_by_key = {}, {}
    homonym_names, multiple_name_keys = set(), set()
    raw_digest, processed_digest = hashlib.sha256(), hashlib.sha256()
    def mismatch(kind, raw_id, processed_id):
        mismatches[kind] += 1
        if len(report['case_references']) < 100:
            report['case_references'].append({'kind': kind, 'raw_id': raw_id, 'processed_id': processed_id})
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with engine.connect().execution_options(isolation_level='REPEATABLE READ') as db:
            report['database_identity'] = configure(db)
            report['before'] = snapshot(db)
            sources = db.execute(text('SELECT id,endpoint FROM fuentes_datos')).all()
            allowed_sources = set()
            report['sources'] = []
            for source_id, endpoint in sources:
                parsed = urlsplit(endpoint)
                assert parsed.scheme == 'https' and parsed.hostname in ('www.datos.gov.co', 'datos.gov.co') and parsed.path.rstrip('/') == '/resource/p6dx-8zbt.json'
                allowed_sources.add(source_id)
                report['sources'].append({'id': source_id, 'host': parsed.hostname, 'path': parsed.path})
            assert allowed_sources
            indexes = [dict(x) for x in db.execute(text("SELECT i.relname,pg_get_indexdef(i.oid) AS definition,ix.indisvalid,ix.indisready FROM pg_index ix JOIN pg_class i ON i.oid=ix.indexrelid WHERE ix.indrelid='raw_secop'::regclass AND ix.indisunique")).mappings()]
            assert any(x['indisvalid'] and x['indisready'] and '(fuente_id, socrata_row_id)' in x['definition'] for x in indexes)
            report['source_row_unique_index_verified'] = True
            raw_sql = 'SELECT id,fuente_id,socrata_row_id,nit_del_proveedor_adjudicado,nombre_del_proveedor FROM raw_secop ORDER BY id'
            processed_sql = 'SELECT id,raw_secop_id,nit_proveedor,nit_proveedor_clave,proveedor_normalizado FROM contratos_procesados ORDER BY raw_secop_id'
            report['read_plans'] = {name: db.execute(text('EXPLAIN (FORMAT JSON) ' + sql)).scalar_one() for name, sql in (('raw', raw_sql), ('processed', processed_sql))}
            save('streaming_full_cut')
            native = db.connection.driver_connection
            raw_cursor = native.cursor(name='p06_raw')
            processed_cursor = native.cursor(name='p06_processed')
            raw_cursor.itersize = processed_cursor.itersize = 10000
            raw_cursor.execute(raw_sql)
            processed_cursor.execute(processed_sql)
            previous_raw = previous_processed_raw = 0
            try:
                for raw, processed in zip_longest(raw_cursor, processed_cursor):
                    if raw is not None:
                        report['evaluated_raw_rows'] += 1
                        raw_id, source_id, source_row_id, reported_nit, reported_name = raw
                        assert raw_id > previous_raw
                        previous_raw = raw_id
                        raw_digest.update(json.dumps(raw, ensure_ascii=False, separators=(',', ':')).encode('utf-8') + b'\n')
                        if source_id not in allowed_sources or not source_row_id:
                            mismatch('missing_or_unexpected_source_provenance', raw_id, None)
                    if processed is not None:
                        report['evaluated_processed_rows'] += 1
                        processed_id, processed_raw_id, stored_nit, stored_key, stored_name = processed
                        assert processed_raw_id > previous_processed_raw
                        previous_processed_raw = processed_raw_id
                        processed_digest.update(json.dumps(processed, ensure_ascii=False, separators=(',', ':')).encode('utf-8') + b'\n')
                    if raw is None or processed is None or raw[0] != processed[1]:
                        mismatch('raw_processed_row_correspondence', raw[0] if raw else None, processed[0] if processed else None)
                        continue
                    expected_nit = normalize_nit(reported_nit)
                    expected_key = normalize_key(reported_nit)
                    expected_name = normalize_name(reported_name)
                    for label, actual, expected in (('reported_nit_normalization', stored_nit, expected_nit), ('canonical_nit_key', stored_key, expected_key), ('reported_supplier_name_normalization', stored_name, expected_name)):
                        if actual != expected:
                            mismatch(label, raw_id, processed_id)
                    if expected_nit is None:
                        category = 'missing_or_known_missing_marker'
                    elif expected_key is not None:
                        category = 'accepted_with_coherent_dv' if '-' in expected_nit else 'accepted_without_dv'
                    else:
                        parts = expected_nit.rsplit('-', 1)
                        body = parts[0]
                        numeric_body = body.isdigit() or bool(re.fullmatch(r'\d{1,3}(?:\.\d{3})+', body)) or bool(re.fullmatch(r'\d{1,3}(?: \d{3})+', body))
                        digits = body.replace('.', '').replace(' ', '')
                        category = 'incoherent_dv' if len(parts) == 2 and len(parts[1]) == 1 and parts[1].isdigit() and numeric_body and 6 <= len(digits) <= 15 else 'unsupported_or_ambiguous_format'
                    classes[category] += 1
                    if expected_key is not None:
                        expected_groups[expected_key] += 1
                        if expected_name:
                            if expected_name in first_key_by_name and first_key_by_name[expected_name] != expected_key:
                                homonym_names.add(expected_name)
                            first_key_by_name.setdefault(expected_name, expected_key)
                            if expected_key in first_name_by_key and first_name_by_key[expected_key] != expected_name:
                                multiple_name_keys.add(expected_key)
                            first_name_by_key.setdefault(expected_key, expected_name)
                    if report['evaluated_raw_rows'] % 100000 == 0:
                        report['classification'] = dict(classes)
                        report['mismatches'] = dict(mismatches)
                        save('streaming_full_cut')
            finally:
                raw_cursor.close()
                processed_cursor.close()
            report['classification'] = dict(classes)
            report['mismatches'] = dict(mismatches)
            report['raw_projection_sha256'] = raw_digest.hexdigest()
            report['processed_projection_sha256'] = processed_digest.hexdigest()
            report['supplier_groups'] = {'accepted_keys': len(expected_groups), 'contracts_with_accepted_key': sum(expected_groups.values()), 'names_with_multiple_distinct_keys': len(homonym_names), 'keys_with_multiple_reported_names': len(multiple_name_keys)}
            assert report['evaluated_raw_rows'] == report['evaluated_processed_rows'] == sum(classes.values()) == 9249545
            assert not mismatches, 'Full-cut discrepancies require inspection; no automatic repair'
            save('verifying_complete_supplier_aggregation')
            grouped = db.execution_options(stream_results=True).execute(text('SELECT nit_proveedor_clave,count(*) FROM contratos_procesados WHERE nit_proveedor_clave IS NOT NULL GROUP BY nit_proveedor_clave'))
            group_count = grouped_rows = 0
            group_digest = hashlib.sha256()
            for key, count in grouped:
                assert key in expected_groups and expected_groups[key] == count
                group_count += 1
                grouped_rows += count
                group_digest.update(json.dumps([key, count], separators=(',', ':')).encode() + b'\n')
            grouped.close()
            db.execution_options(stream_results=False)
            assert group_count == len(expected_groups) and grouped_rows == sum(expected_groups.values())
            report['all_supplier_group_counts_match'] = True
            report['group_result_sha256'] = group_digest.hexdigest()
            session = Session(bind=db)
            try:
                ranking = TransformacionRepository(session).get_top_providers(limit=100)
                assert len(ranking) == min(100, len(expected_groups))
                assert len({x['nit'] for x in ranking}) == len(ranking)
                assert all(expected_groups[x['nit']] == x['contracts'] for x in ranking)
                assert [x['contracts'] for x in ranking] == sorted(expected_groups.values(), reverse=True)[:100]
                report['repository_top_provider_groups_verified'] = len(ranking)
            finally:
                session.close()
            report['after_same_snapshot'] = snapshot(db)
            assert report['before'] == report['after_same_snapshot']
        with engine.connect().execution_options(isolation_level='REPEATABLE READ') as db:
            configure(db)
            report['after_fresh_snapshot'] = snapshot(db)
            assert report['before'] == report['after_fresh_snapshot']
        assert bindings() == initial_bindings
        report.update(active_published_bindings_unchanged=True, bounded_state_and_controls_unchanged=True, database_transaction_mode='REPEATABLE READ, READ ONLY', completed_at_utc=datetime.now(timezone.utc).isoformat())
        save('verified_full_cut_secop_supplier_consistency')
    except Exception as exc:
        report['error_type'] = type(exc).__name__
        report['error_frames'] = [{'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name} for frame in traceback.extract_tb(exc.__traceback__)]
        save('stopped_for_inspection')
        raise SystemExit(1) from None
    finally:
        engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--integration-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.integration_root, args.output)
