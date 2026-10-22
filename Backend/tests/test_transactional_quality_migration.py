import importlib.util
from pathlib import Path


def _migration():
    path=Path(__file__).resolve().parents[1]/'database/migrations/versions/2ab7c4e8d910_transactional_quality_metrics.py'
    spec=importlib.util.spec_from_file_location('quality_summary_migration',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_locks_backfills_and_registers_statement_triggers_atomically(monkeypatch):
    m=_migration()
    events=[]
    monkeypatch.setattr(m.op,'execute',lambda sql:events.append(str(sql)))
    monkeypatch.setattr(m.op,'create_table',lambda *args,**kwargs:events.append('CREATE TABLE'))
    m.upgrade()
    assert 'transaction_isolation' in events[0] and "<> 'read committed'" in events[0]
    lock=next(i for i,sql in enumerate(events) if sql.startswith('LOCK TABLE'))
    backfill=next(i for i,sql in enumerate(events) if sql.startswith('INSERT INTO'))
    triggers=[i for i,sql in enumerate(events) if 'CREATE TRIGGER' in sql]
    assert lock<backfill<min(triggers)
    assert len(triggers)==4
    assert sum('FOR EACH STATEMENT' in events[i] for i in triggers)==3
    update=next(events[i] for i in triggers if 'AFTER UPDATE' in events[i])
    assert 'FOR EACH ROW' in update and 'IS DISTINCT FROM' in update
    assert 'SHARE ROW EXCLUSIVE' in events[lock]
    assert not any('COMMIT' in sql or 'autocommit' in sql for sql in events)
    assert m.down_revision=='08c6d9a2e4b1'


def test_trigger_functions_use_caller_privileges_and_skip_zero_delta():
    m=_migration()
    for event in ('insert','update','delete'):
        sql=m._function(event)
        assert 'SECURITY DEFINER' not in sql
        assert 'SET search_path = pg_catalog, pg_temp' in sql
        assert 'UPDATE public.contratos_metricas_calidad' in sql
        if event != 'update':
            assert 'IF d_total<>0' in sql and 'd_sum<>0' in sql
        assert 'Missing transactional contract quality summary' in sql
        assert 'IF NOT FOUND' in sql
    assert 'NEW.nivel_confianza::numeric' in m._function('update')
    assert 'OLD.nivel_confianza::numeric' in m._function('update')
    assert 'FROM old_contracts' in m._function('delete')
    assert 'FROM new_contracts' in m._function('insert')


def test_downgrade_removes_only_summary_objects(monkeypatch):
    m=_migration()
    events=[]
    monkeypatch.setattr(m.op,'execute',lambda sql:events.append(str(sql)))
    monkeypatch.setattr(m.op,'drop_table',lambda name,**kwargs:events.append('DROP TABLE '+name))
    m.downgrade()
    assert sum(sql.startswith('DROP TRIGGER') for sql in events)==4
    assert sum(sql.startswith('DROP FUNCTION') for sql in events)==4
    assert events[-1]=='DROP TABLE contratos_metricas_calidad'
    assert not any('DELETE FROM' in sql or 'TRUNCATE' in sql for sql in events)
