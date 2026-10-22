from contextlib import contextmanager
import importlib.util
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex
from sqlalchemy.orm import Session

from modules.transformacion.repository.transformacion import TransformacionRepository
from modules.transformacion.model.ContratoProcesado import ContratoProcesado


def test_ranking_limits_identity_groups_before_reading_names_in_one_statement():
    engine = create_engine('sqlite://')
    statements = []
    try:
        with engine.begin() as db:
            db.exec_driver_sql('CREATE TABLE contratos_procesados (id INTEGER PRIMARY KEY, nit_proveedor_clave TEXT, proveedor_normalizado TEXT)')
            db.exec_driver_sql("INSERT INTO contratos_procesados VALUES (1,'1','A'),(2,'1','Z'),(3,'2',NULL),(4,'2',NULL),(5,'3','Z'),(6,'3','Z'),(7,NULL,'Z')")
        event.listen(engine, 'before_cursor_execute', lambda _db,_cursor,sql,_params,_context,_many: statements.append(sql))
        with Session(engine) as session:
            result = TransformacionRepository(session).get_top_providers(limit=2)
        assert result == [{'nit':'1','name':'Z','contracts':2},{'nit':'2','name':'2','contracts':2}]
        assert len(statements) == 1
        sql = statements[0].lower()
        ranking_sql = sql.split('from (select ', 1)[1]
        assert 'count(*)' in ranking_sql and 'limit' in ranking_sql
        assert 'proveedor_normalizado' not in ranking_sql
        assert 'max(contratos_procesados.proveedor_normalizado)' in sql
    finally:
        engine.dispose()


def test_supplier_index_covers_names_only_for_identified_suppliers():
    index = next(i for i in ContratoProcesado.__table__.indexes if i.name=='ix_cp_nit_nombre')
    sql = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    assert '(nit_proveedor_clave, proveedor_normalizado)' in sql
    assert 'WHERE nit_proveedor_clave IS NOT NULL' in sql
    assert not index.unique


def test_supplier_index_migration_is_additive_and_concurrent(monkeypatch):
    path=Path(__file__).resolve().parents[1]/'database/migrations/versions/f4826b9d1c30_cover_provider_ranking.py'
    spec=importlib.util.spec_from_file_location('supplier_ranking_migration',path)
    migration=importlib.util.module_from_spec(spec); spec.loader.exec_module(migration)
    events=[]
    class Context:
        @contextmanager
        def autocommit_block(self):
            events.append('autocommit'); yield
    monkeypatch.setattr(migration.op,'get_context',lambda: Context())
    monkeypatch.setattr(migration.op,'create_index',lambda *args,**kw: events.append(('create',args,kw)))
    monkeypatch.setattr(migration.op,'drop_index',lambda *args,**kw: events.append(('drop',args,kw)))
    migration.upgrade(); migration.downgrade()
    assert migration.down_revision=='e3915a6c7d82'
    assert events[0]==events[2]=='autocommit'
    assert events[1][2]['postgresql_concurrently'] is True
    assert str(events[1][2]['postgresql_where'])=='nit_proveedor_clave IS NOT NULL'
    assert events[3][2]['postgresql_concurrently'] is True
