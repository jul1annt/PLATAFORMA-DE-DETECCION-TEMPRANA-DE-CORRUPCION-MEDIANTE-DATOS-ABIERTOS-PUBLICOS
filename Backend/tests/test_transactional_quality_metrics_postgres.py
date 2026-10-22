"""Exact summaries under native DML, savepoints and concurrent transactions."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError, NoResultFound
from sqlalchemy.orm import Session

from modules.transformacion.repository.transformacion import TransformacionRepository
from citizen_history_fixture import OwnedCitizenHistory

DIRECT = """SELECT count(*) AS total,count(*) FILTER (WHERE es_incompleto IS TRUE) AS incompletos,
 count(*) FILTER (WHERE es_sospechoso IS TRUE) AS sospechosos,
 count(*) FILTER (WHERE clasificacion_riesgo='ALTO') AS alto_riesgo,
 count(nivel_confianza) AS con_confianza,coalesce(sum(nivel_confianza::numeric),0) AS suma_confianza
 FROM public.contratos_procesados"""


def _assert_exact(session):
    # One statement, therefore one snapshot even with concurrent commits.
    row = session.execute(text(f"""SELECT
      (s.total,s.incompletos,s.sospechosos,s.alto_riesgo,s.con_confianza,s.suma_confianza)
      IS NOT DISTINCT FROM (d.total,d.incompletos,d.sospechosos,d.alto_riesgo,d.con_confianza,d.suma_confianza)
      FROM public.contratos_metricas_calidad s CROSS JOIN ({DIRECT}) d WHERE s.id=1""")).scalar_one()
    assert row is True


def _raw(session, count=3):
    source = session.execute(text("""INSERT INTO fuentes_datos(nombre,tipo,formato,endpoint,activo,frecuencia_dias)
      VALUES (:name,'TEST','JSON','https://example.test/metrics',false,15) RETURNING id"""), {'name': 'quality-' + uuid.uuid4().hex}).scalar_one()
    ids = []
    for index in range(count):
        ids.append(session.execute(text("INSERT INTO raw_secop(fuente_id,id_del_proceso) VALUES(:source,:process) RETURNING id"), {'source': source,'process': 'quality-' + uuid.uuid4().hex}).scalar_one())
    return ids


def _insert(session, raw_ids):
    rows = [{'raw': raw, 'hash': uuid.uuid4().hex, 'incomplete': index % 2 == 0, 'suspicious': index % 3 == 0, 'confidence': None if index == 0 else index * 20, 'risk': 'ALTO' if index % 2 else 'SIN_EVALUAR'} for index,raw in enumerate(raw_ids)]
    session.execute(text("""INSERT INTO contratos_procesados(raw_secop_id,normalized_hash,es_incompleto,es_sospechoso,nivel_confianza,clasificacion_riesgo)
       VALUES(:raw,:hash,:incomplete,:suspicious,:confidence,:risk)"""), rows)
    return rows


def test_triggers_are_enabled_with_a_guarded_row_update(postgres_test_session):
    rows = postgres_test_session.execute(text("""SELECT tgname,tgenabled,(tgtype & 1)=0 AS statement
      FROM pg_trigger WHERE tgrelid='public.contratos_procesados'::regclass AND tgname LIKE 'trg_contract_quality_%' ORDER BY tgname""")).all()
    assert len(rows) == 4 and all(enabled == 'O' for _,enabled,_ in rows)
    assert {name:statement for name,_,statement in rows} == {
        'trg_contract_quality_insert':True,'trg_contract_quality_update':False,
        'trg_contract_quality_delete':True,'trg_contract_quality_truncate':True,
    }
    _assert_exact(postgres_test_session)


def test_insert_update_delete_zero_rows_and_timestamp_only_are_exact(postgres_test_session):
    s = postgres_test_session
    raw = _raw(s)
    _insert(s,raw)
    _assert_exact(s)
    before = s.execute(text('SELECT ctid::text FROM public.contratos_metricas_calidad WHERE id=1')).scalar_one()
    s.execute(text('UPDATE contratos_procesados SET procesado_en=:now WHERE raw_secop_id=ANY(:ids)'), {'now':datetime.now(timezone.utc),'ids':raw})
    assert s.execute(text('SELECT ctid::text FROM public.contratos_metricas_calidad WHERE id=1')).scalar_one() == before
    s.execute(text("UPDATE contratos_procesados SET es_incompleto=NULL,es_sospechoso=NULL,nivel_confianza=0,clasificacion_riesgo='BAJO' WHERE raw_secop_id=ANY(:ids)"), {'ids':raw})
    _assert_exact(s)
    s.execute(text('DELETE FROM contratos_procesados WHERE raw_secop_id=:id'), {'id':raw[0]})
    _assert_exact(s)
    before = s.execute(text('SELECT ctid::text FROM public.contratos_metricas_calidad WHERE id=1')).scalar_one()
    s.execute(text('UPDATE contratos_procesados SET nivel_confianza=90 WHERE false'))
    s.execute(text('DELETE FROM contratos_procesados WHERE false'))
    s.execute(text("INSERT INTO contratos_procesados(raw_secop_id,normalized_hash,clasificacion_riesgo) SELECT 0,'unused','SIN_EVALUAR' WHERE false"))
    assert s.execute(text('SELECT ctid::text FROM public.contratos_metricas_calidad WHERE id=1')).scalar_one() == before
    _assert_exact(s)


def test_multirow_upsert_and_do_nothing_do_not_double_count(postgres_test_session):
    s=postgres_test_session
    raw=_raw(s)
    _insert(s,raw[:1])
    s.execute(text("""INSERT INTO contratos_procesados(raw_secop_id,normalized_hash,es_incompleto,es_sospechoso,nivel_confianza,clasificacion_riesgo)
      VALUES(:one,'new1',true,false,90,'ALTO'),(:two,'new2',false,true,0,'MEDIO'),(:three,'new3',false,false,NULL,'BAJO')
      ON CONFLICT(raw_secop_id) DO UPDATE SET es_incompleto=EXCLUDED.es_incompleto,
      es_sospechoso=EXCLUDED.es_sospechoso,nivel_confianza=EXCLUDED.nivel_confianza,clasificacion_riesgo=EXCLUDED.clasificacion_riesgo"""),dict(zip(('one','two','three'),raw)))
    _assert_exact(s)
    before=s.execute(text('SELECT ctid::text FROM public.contratos_metricas_calidad WHERE id=1')).scalar_one()
    s.execute(text("INSERT INTO contratos_procesados(raw_secop_id,normalized_hash,clasificacion_riesgo) VALUES(:id,'ignored','BAJO') ON CONFLICT(raw_secop_id) DO NOTHING"),{'id':raw[0]})
    assert s.execute(text('SELECT ctid::text FROM public.contratos_metricas_calidad WHERE id=1')).scalar_one()==before
    _assert_exact(s)


def test_equal_net_delta_keeps_exact_summary(postgres_test_session):
    s=postgres_test_session
    raw=_raw(s,2)
    _insert(s,raw)
    s.execute(text('UPDATE contratos_procesados SET nivel_confianza=50 WHERE raw_secop_id=ANY(:ids)'),{'ids':raw})
    before=s.execute(text('SELECT total,suma_confianza FROM public.contratos_metricas_calidad WHERE id=1')).one()
    s.execute(text('UPDATE contratos_procesados SET nivel_confianza=CASE WHEN raw_secop_id=:one THEN 0 ELSE 100 END WHERE raw_secop_id=ANY(:ids)'),{'one':raw[0],'ids':raw})
    assert s.execute(text('SELECT total,suma_confianza FROM public.contratos_metricas_calidad WHERE id=1')).one()==before
    _assert_exact(s)


def test_summary_and_contracts_roll_back_together_at_savepoint(postgres_test_session):
    s=postgres_test_session
    baseline=s.execute(text('SELECT total,suma_confianza FROM public.contratos_metricas_calidad WHERE id=1')).one()
    with pytest.raises(RuntimeError):
        with s.begin_nested():
            _insert(s,_raw(s))
            _assert_exact(s)
            raise RuntimeError('Abort batch after summary changed')
    assert s.execute(text('SELECT total,suma_confianza FROM public.contratos_metricas_calidad WHERE id=1')).one()==baseline
    _assert_exact(s)


def test_truncate_and_rollback_preserve_exact_summary(postgres_test_session):
    s=postgres_test_session
    _insert(s,_raw(s))
    # A complete truncate would destroy reversible citizen versions. The new
    # policy refuses it before any source row or metric can disappear.
    with pytest.raises(DBAPIError,match='Conservar versiones ciudadanas'):
        with s.begin_nested():
            s.execute(text('TRUNCATE public.contratos_procesados CASCADE'))
    _assert_exact(s)


def test_missing_summary_row_fails_reads_and_writes(postgres_test_session):
    s=postgres_test_session
    raw=_raw(s,1)
    savepoint = s.begin_nested()
    try:
        s.execute(text('DELETE FROM public.contratos_metricas_calidad WHERE id=1'))
        with pytest.raises(NoResultFound):
            TransformacionRepository(s).get_metricas_calidad()
        with pytest.raises(DBAPIError):
            with s.begin_nested():
                _insert(s,raw)
        assert s.execute(text('SELECT count(*) FROM contratos_procesados WHERE raw_secop_id=:id'),{'id':raw[0]}).scalar_one()==0
    finally:
        savepoint.rollback()
    _assert_exact(s)


def test_summary_read_respects_autoflush_and_reuses_presence_check(postgres_test_session):
    from modules.transformacion.model.ContratoProcesado import ContratoProcesado
    s=postgres_test_session
    raw=_raw(s,1)[0]
    previous=s.execute(text('SELECT total FROM public.contratos_metricas_calidad WHERE id=1')).scalar_one()
    s.add(ContratoProcesado(raw_secop_id=raw,normalized_hash=uuid.uuid4().hex,es_incompleto=False,es_sospechoso=False,nivel_confianza=0,clasificacion_riesgo='ALTO'))
    repo=TransformacionRepository(s)
    assert repo.get_dashboard_metricas()['total_contratos']==previous+1
    statements=[]
    bind=s.get_bind()
    def capture(conn,cursor,statement,params,context,many):
        statements.append(statement)
    event.listen(bind,'before_cursor_execute',capture)
    try:
        assert repo.get_metricas_calidad()['total_contratos']==previous+1
    finally:
        event.remove(bind,'before_cursor_execute',capture)
    assert len(statements)==1
    assert 'contratos_metricas_calidad' in statements[0] and 'contratos_procesados' not in statements[0]
    _assert_exact(s)


@pytest.mark.parametrize('confidence', [(None,None),(0,0),(1,2),(-2147483648,2147483647)])
def test_summary_matches_legacy_values_with_null_zero_fraction_or_extreme_confidence(postgres_test_session,confidence):
    s=postgres_test_session
    raw=_raw(s,2)
    _insert(s,raw)
    for raw_id,value in zip(raw,confidence):
        s.execute(text('UPDATE contratos_procesados SET es_incompleto=NULL,es_sospechoso=NULL,nivel_confianza=:value WHERE raw_secop_id=:id'),{'value':value,'id':raw_id})
    summary_repo=TransformacionRepository(s)
    quality=summary_repo.get_metricas_calidad()
    dashboard=summary_repo.get_dashboard_metricas()
    anomalies=summary_repo.get_anomaly_distribution()
    s.info['contract_quality_summary_available']=False
    legacy_repo=TransformacionRepository(s)
    assert quality==legacy_repo.get_metricas_calidad()
    assert dashboard==legacy_repo.get_dashboard_metricas()
    assert anomalies==legacy_repo.get_anomaly_distribution()
    _assert_exact(s)


def test_sqlite_keeps_original_aggregate_without_summary():
    engine=create_engine('sqlite://')
    try:
        with engine.begin() as c:
            c.exec_driver_sql('CREATE TABLE contratos_procesados(id INTEGER PRIMARY KEY,es_incompleto BOOLEAN,es_sospechoso BOOLEAN,clasificacion_riesgo TEXT,nivel_confianza INTEGER)')
            c.exec_driver_sql("INSERT INTO contratos_procesados VALUES(1,1,0,'ALTO',0)")
        with Session(engine) as s:
            assert TransformacionRepository(s).get_metricas_calidad()['promedio_confianza']==0
    finally:
        engine.dispose()


def test_parallel_committed_writers_and_reader_observe_exact_totals(postgres_test_session):
    # Separate ordinary-role connections, real commits. Clean only our synthetic rows.
    engine=create_engine(postgres_test_session.connection().engine.url,pool_size=4,max_overflow=0)
    owned_history=OwnedCitizenHistory(engine)
    source_ids=[]
    try:
        with engine.begin() as c:
            for index in range(2):
                source_ids.append(c.execute(text("INSERT INTO fuentes_datos(nombre,tipo,formato,endpoint,activo,frecuencia_dias) VALUES(:name,'TEST','JSON','https://example.test/concurrent-quality',false,15) RETURNING id"),{'name':'quality-concurrent-'+uuid.uuid4().hex}).scalar_one())
        def writer(source):
            for batch in range(3):
                with engine.begin() as c:
                    c.execute(text("SET LOCAL lock_timeout='10s'"))
                    raw=c.execute(text('INSERT INTO raw_secop(fuente_id,id_del_proceso) VALUES(:source,:process) RETURNING id'),{'source':source,'process':uuid.uuid4().hex}).scalar_one()
                    c.execute(text("INSERT INTO contratos_procesados(raw_secop_id,normalized_hash,es_incompleto,es_sospechoso,nivel_confianza,clasificacion_riesgo) VALUES(:raw,:hash,true,false,90,'ALTO')"),{'raw':raw,'hash':uuid.uuid4().hex})
        def reader():
            for _ in range(15):
                with Session(engine) as s:
                    _assert_exact(s)
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures=[pool.submit(writer,source) for source in source_ids]+[pool.submit(reader)]
            for future in futures:
                future.result(timeout=30)
        with Session(engine) as s:
            _assert_exact(s)
            assert s.execute(text('SELECT count(*) FROM contratos_procesados c JOIN raw_secop r ON r.id=c.raw_secop_id WHERE r.fuente_id=ANY(:sources)'),{'sources':source_ids}).scalar_one()==6
    finally:
        with engine.begin() as c:
            owned_raw_ids=c.execute(text('SELECT id FROM raw_secop WHERE fuente_id=ANY(:sources)'),{'sources':source_ids}).scalars().all()
            c.execute(text('DELETE FROM contratos_procesados WHERE raw_secop_id IN (SELECT id FROM raw_secop WHERE fuente_id=ANY(:sources))'),{'sources':source_ids})
            c.execute(text('DELETE FROM raw_secop WHERE fuente_id=ANY(:sources)'),{'sources':source_ids})
            c.execute(text('DELETE FROM fuentes_datos WHERE id=ANY(:sources)'),{'sources':source_ids})
        owned_history.cleanup(owned_raw_ids)
        engine.dispose()
