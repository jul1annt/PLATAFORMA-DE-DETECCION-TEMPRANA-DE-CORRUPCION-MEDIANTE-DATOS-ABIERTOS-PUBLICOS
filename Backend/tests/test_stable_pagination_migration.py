from contextlib import contextmanager
import importlib.util
from pathlib import Path
import pytest


def migration(monkeypatch, states):
    path=Path(__file__).resolve().parents[1]/'database/migrations/versions/3c19a8f7e2d0_stable_contract_pagination.py'
    spec=importlib.util.spec_from_file_location('pagination_migration',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    events=[]
    class Context:
        @contextmanager
        def autocommit_block(self):
            events.append('autocommit');yield
    results=iter(states)
    monkeypatch.setattr(module.op,'get_context',lambda:Context())
    monkeypatch.setattr(module,'_index',lambda:next(results))
    monkeypatch.setattr(module.op,'create_index',lambda *a,**kw:events.append(('create',a,kw)))
    monkeypatch.setattr(module.op,'drop_index',lambda *a,**kw:events.append(('drop',a,kw)))
    return module,events


def definition():
    return dict(valid=True,ready=True,unique=False,plain=True,method='btree',
                table_schema='public',table_name='contratos_procesados',key_count=2,column_count=2,
                columns=['fecha_publicacion_normalizada','id'],option_flags=[0,0])


def test_create_and_verify_concurrent_date_id_index(monkeypatch):
    module,events=migration(monkeypatch,[None,definition()]);module.upgrade()
    assert module.down_revision=='2ab7c4e8d910'
    assert len(events)==2 and events[1][0]=='create'
    assert events[1][1][2]==['fecha_publicacion_normalizada','id']
    assert events[1][2]['postgresql_concurrently'] is True


def test_upgrade_reuses_verified_existing_index(monkeypatch):
    module,events=migration(monkeypatch,[definition()]);module.upgrade()
    assert events==['autocommit']


@pytest.mark.parametrize('key,value', [('valid',False),('ready',False),('unique',True),
    ('plain',False),('method','hash'),('table_schema','other'),('table_name','other'),
    ('key_count',1),('column_count',3),('columns',['id','fecha_publicacion_normalizada']),('option_flags',[0,1])])
def test_mismatched_index_is_preserved_on_upgrade_and_downgrade(monkeypatch,key,value):
    bad=definition();bad[key]=value
    module,events=migration(monkeypatch,[bad,bad])
    with pytest.raises(RuntimeError):module.upgrade()
    with pytest.raises(RuntimeError):module.downgrade()
    assert events==['autocommit','autocommit']


def test_downgrade_removes_only_verified_index_concurrently(monkeypatch):
    module,events=migration(monkeypatch,[definition()]);module.downgrade()
    assert events[1][0]=='drop' and events[1][1][0]==module.NAME
    assert events[1][2]['postgresql_concurrently'] is True


def test_downgrade_without_index_is_safe(monkeypatch):
    module,events=migration(monkeypatch,[None]);module.downgrade()
    assert events==['autocommit']
