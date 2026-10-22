"""Measure feature preparation on an explicit isolated copy; never score or publish."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import statistics
import sys
import threading
import time
from dotenv import dotenv_values
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.motor_riesgo.history import prepare_context
from modules.motor_riesgo.feature_store import fetch_batch
from modules.motor_riesgo.feature_builder import build_observation, capture_stage
from modules.motor_riesgo.domain import canonical, identity_reasons, features


def summary(values):
    ordered = sorted(values)
    return {'requests': len(values), 'median_ms': statistics.median(values) if values else None,
            'p95_ms': ordered[max(0, math.ceil(.95 * len(values)) - 1)] if values else None,
            'max_ms': max(values) if values else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env', type=Path, required=True)
    parser.add_argument('--database', required=True)
    parser.add_argument('--expected-oid', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    values = dotenv_values(args.env)
    if (values['DB_HOST'] not in {'127.0.0.1', 'localhost', '::1'} or values['DB_PORT'] != '5433'
            or 'test' not in args.database.lower() or args.expected_oid in {24577, 37886, 74053}
            or args.output.exists()):
        raise SystemExit('Se requiere copia de pruebas explícita en 5433, identidad separada y salida nueva')
    root = Path(__file__).resolve().parents[1]
    minimum_free = shutil.disk_usage(root).free
    if minimum_free < 33 * 1024**3:
        raise SystemExit('Conservar reserva de 25 GiB más margen de 8 GiB para tablas temporales')
    url = URL.create('postgresql', username=values['DB_USER'], password=values['DB_PASSWORD'],
                     host=values['DB_HOST'], port=5433, database=args.database)
    engine = create_engine(url, hide_parameters=True, pool_size=2, max_overflow=0, connect_args={'connect_timeout': 10})
    phases = []
    projection_rows = 0

    @event.listens_for(engine, 'before_cursor_execute')
    def guard(_connection, _cursor, statement, _parameters, context, _many):
        sql = statement.strip()
        temporary_insert = bool(re.match(r'^INSERT INTO pg_temp\.risk_capture_base\s', sql))
        temporary_alter = sql == 'ALTER TABLE pg_temp.risk_capture_base RENAME TO risk_capture_rows'
        permitted = (sql.upper().startswith(('SELECT ', 'WITH ', 'SET ', 'EXPLAIN (FORMAT JSON) ')) or
                     temporary_insert or
                     temporary_alter or
                     sql == 'LOCK TABLE raw_secop,contratos_procesados IN SHARE MODE' or
                     re.match(r'^CREATE TEMP TABLE risk_[a-z_]+ AS\s', sql) or
                     re.match(r'^CREATE (UNIQUE )?INDEX ON risk_[a-z_]+\(', sql) or
                     re.match(r'^DROP TABLE(?: IF EXISTS)? pg_temp\.risk_[a-z_]+$', sql) or
                     re.match(r'^ANALYZE pg_temp\.risk_[a-z_]+$', sql))
        if (not permitted or re.search(r'\b(UPDATE|DELETE|TRUNCATE|GRANT|REVOKE)\b', sql, re.I)
                or (not temporary_alter and re.search(r'\bALTER\b',sql,re.I))
                or (not temporary_insert and re.search(r'\bINSERT\b', sql, re.I))):
            raise RuntimeError('El ensayo prohíbe escrituras fuera de sus tablas temporales')
        context._risk_started = time.perf_counter()
        if sql.upper().startswith('CREATE '):
            print(json.dumps({'phase_started': sql.splitlines()[0]}), flush=True)

    @event.listens_for(engine, 'after_cursor_execute')
    def measure(_connection, _cursor, statement, _parameters, context, _many):
        nonlocal projection_rows
        if statement.strip().startswith('INSERT INTO pg_temp.risk_capture_base'):
            projection_rows += _cursor.rowcount
            if projection_rows % 1_000_000 == 0 or projection_rows <= 100000:
                print(json.dumps({'projection_rows': projection_rows}), flush=True)
        if statement.strip().upper().startswith(('CREATE ', 'ANALYZE ')):
            phase = {'sql': statement.strip().splitlines()[0], 'seconds': round(time.perf_counter()-context._risk_started, 3)}
            phases.append(phase)
            print(json.dumps(phase), flush=True)

    stop = threading.Event()
    during, reader_errors = [], []
    reader = None
    failure = None
    report = {'time': datetime.now(timezone.utc).isoformat(), 'status': 'FAILED', 'phases': phases,
              'real_models_activated': 0, 'publication_performed': False}
    implementation = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in (
        'modules/motor_riesgo/history.py','modules/motor_riesgo/feature_store.py',
        'modules/motor_riesgo/feature_builder.py','modules/motor_riesgo/domain.py','modules/motor_riesgo/materialize.py')}
    try:
        # The outer transaction retains SHARE locks across service commits.
        # They allow readers but prevent writes to this isolated source copy.
        with engine.connect() as connection, connection.begin(), Session(bind=connection) as db:
            identity = db.execute(text('''SELECT current_database(),current_user,
                (SELECT oid FROM pg_database WHERE datname=current_database()),
                (SELECT rolsuper FROM pg_roles WHERE rolname=current_user),pg_backend_pid()''')).one()
            if identity[0] != args.database or identity[2] != args.expected_oid or identity[3]:
                raise ValueError('Identidad o rol de la copia incorrectos')
            db.execute(text("SET statement_timeout='600s'"))
            db.execute(text("SET lock_timeout='2s'"))
            db.execute(text('SET max_parallel_workers_per_gather=0'))
            db.execute(text('LOCK TABLE raw_secop,contratos_procesados IN SHARE MODE'))
            if db.execute(text('SELECT count(*) FROM fuentes_datos WHERE activo')).scalar_one():
                raise ValueError('La copia debe conservar sus fuentes pausadas')
            if db.execute(text('SELECT count(*) FROM background_jobs WHERE active')).scalar_one():
                raise ValueError('La copia tiene trabajos activos; revisar antes de medir')
            sources = list(db.execute(text("SELECT id FROM fuentes_datos WHERE endpoint LIKE '%/p6dx-8zbt.json'")).scalars())
            if not sources:
                raise ValueError('La copia no contiene la fuente esperada')
            before = [db.execute(text('SELECT count(*) FROM raw_secop WHERE fuente_id=ANY(:sources)'), {'sources': sources}).scalar_one(),
                      db.execute(text('SELECT max(id) FROM raw_secop')).scalar_one()]
            norm_before = [db.execute(text('SELECT count(*) FROM contratos_procesados')).scalar_one()]
            ids = list(db.execute(text('SELECT raw_secop_id FROM contratos_procesados ORDER BY id DESC LIMIT 200')).scalars())
            db.commit()
            print(json.dumps({'copy_verified': True, 'oid': identity[2], 'postgres_pid': identity[4], 'source_rows': before[0], 'normalized_rows': norm_before[0]}), flush=True)
            if before[0] < 1_000_000 or not ids:
                raise ValueError('El ensayo de volumen requiere una copia con al menos un millón de filas')

            def reads(result, count=None):
                nonlocal minimum_free
                try:
                    with engine.connect().execution_options(postgresql_readonly=True) as reader_db:
                        reader_db.execute(text("SET statement_timeout='15s'"))
                        index = 0
                        while not stop.is_set() and (count is None or index < count):
                            started = time.perf_counter()
                            reader_db.execute(text('SELECT id,id_del_proceso,valor_total_normalizado FROM contratos_procesados WHERE raw_secop_id=:id'),
                                              {'id': ids[index % len(ids)]}).fetchall()
                            reader_db.commit()
                            result.append((time.perf_counter()-started)*1000)
                            minimum_free = min(minimum_free, shutil.disk_usage(root).free)
                            index += 1
                            if count is None:
                                stop.wait(.5)
                except Exception as exc:
                    reader_errors.append(type(exc).__name__)

            baseline = []
            reads(baseline, 30)
            reader = threading.Thread(target=reads, args=(during,), daemon=True)
            reader.start()
            at = datetime.now(timezone.utc).isoformat()
            started = time.perf_counter()
            captured = prepare_context(db, sources, at)
            if captured != before[0]:
                raise ValueError('La proyección no cubre todas las filas de la copia')
            preparation_seconds = time.perf_counter()-started
            stage_counts, exclusions, missing, abstentions = Counter(), Counter(), Counter(), Counter()
            checksum = hashlib.sha256()
            samples, fetch_times = 0, []
            plans = []
            class Explain:
                def execute(self, statement, parameters):
                    return db.execute(text('EXPLAIN (FORMAT JSON) '+str(statement)), parameters)
            # Five bounded batches across the ID range; this is not a claim of
            # representative prevalence or a full-cut inference benchmark.
            for fraction in (0, .25, .5, .75, .99):
                plans.append(fetch_batch(Explain(), sources, int(before[1]*fraction))[0]['QUERY PLAN'])
                fetched = time.perf_counter()
                batch = fetch_batch(db, sources, int(before[1]*fraction))
                fetch_times.append(time.perf_counter()-fetched)
                print(json.dumps({'batch_fraction':fraction,'rows':len(batch),'seconds':round(fetch_times[-1],3)}),flush=True)
                for row in batch:
                    samples += 1
                    observation = build_observation(row, at)
                    if observation is None:
                        exclusions[capture_stage(row, at)[1]] += 1
                        continue
                    stage = observation['stage']
                    stage_counts[stage] += 1
                    abstentions.update(identity_reasons(observation, stage))
                    feature_values, _ = features(observation, stage)
                    missing.update(f'{stage}:{name}' for name,value in feature_values.items() if value is None)
                    checksum.update(canonical(observation))
                db.commit()
            lock_count=db.execute(text("SELECT count(*) FROM pg_locks WHERE pid=pg_backend_pid() AND mode='ShareLock' AND granted AND relation IN ('raw_secop'::regclass,'contratos_procesados'::regclass)")).scalar_one()
            if lock_count != 2:
                raise ValueError('Se perdió la protección de la copia durante el ensayo')
            report = {'time': at, 'status': 'COMPLETE', 'scope': 'Históricos sobre copia completa; cinco lotes de variables y un lector SQL concurrente.',
                      'database': args.database, 'oid': identity[2], 'role': identity[1], 'source_rows': before[0],
                      'normalized_rows': norm_before[0], 'source_tables_unchanged': True, 'non_temp_writes_blocked': True,
                      'projection_rows': captured,
                      'postgres_parallel_workers_per_gather': 0, 'work_mem': '32MB', 'preparation_seconds': preparation_seconds,
                      'phases': phases, 'sample_rows_read': samples, 'sample_stage_counts': dict(stage_counts),
                      'sample_exclusions': dict(exclusions), 'sample_identity_abstentions': dict(abstentions),
                      'sample_missing_features': dict(missing), 'sample_sha256': checksum.hexdigest(),
                      'batch_fetch_seconds': fetch_times, 'baseline_reader': summary(baseline),
                      'batch_query_plans': plans, 'implementation_sha256': implementation,
                      'limitations': ['No entrenamiento ni inferencia con modelos reales.', 'No es prueba completa de API/HTTP ni carga con muchos usuarios.',
                                      'No se recorren ni escriben todos los resultados; no se extrapola el tiempo del corte.'],
                      'real_models_activated': 0, 'publication_performed': False}
    except Exception as exc:
        failure = type(exc).__name__
        report.update(error_type=failure, postgres_error_code=getattr(getattr(exc,'orig',None),'pgcode',None))
    finally:
        stop.set()
        if reader:
            reader.join(20)
        engine.dispose()
    report.update(concurrent_reader=summary(during), reader_errors=reader_errors, minimum_free_disk_bytes=minimum_free)
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(json.dumps({'report': str(args.output), 'status': report['status'], 'preparation_seconds': report.get('preparation_seconds'), 'reader_errors': reader_errors}), flush=True)
    if failure:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
