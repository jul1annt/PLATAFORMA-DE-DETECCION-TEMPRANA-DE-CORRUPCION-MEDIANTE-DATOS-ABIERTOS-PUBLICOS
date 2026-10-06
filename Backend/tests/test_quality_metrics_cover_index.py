from contextlib import contextmanager
import importlib.util
from pathlib import Path
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from modules.transformacion.model.ContratoProcesado import ContratoProcesado


def test_metrics_index_covers_all_aggregate_columns_including_nonnull_id():
    index = next(index for index in ContratoProcesado.__table__.indexes if index.name == 'ix_cp_metricas_cover')
    sql = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    assert '(es_incompleto, es_sospechoso, clasificacion_riesgo, nivel_confianza)' in sql
    assert 'INCLUDE (id)' in sql
    assert not index.unique


def test_additive_metrics_index_migration_uses_concurrent_ddl(monkeypatch):
    path = Path(__file__).resolve().parents[1]/'database/migrations/versions/e3915a6c7d82_cover_quality_metrics.py'
    specification = importlib.util.spec_from_file_location('metrics_cover_migration', path)
    migration = importlib.util.module_from_spec(specification); specification.loader.exec_module(migration)
    events = []
    class Context:
        @contextmanager
        def autocommit_block(self):
            events.append('autocommit')
            yield
    monkeypatch.setattr(migration.op, 'get_context', lambda: Context())
    monkeypatch.setattr(migration.op, 'create_index', lambda *args, **kwargs: events.append(('create',args,kwargs)))
    monkeypatch.setattr(migration.op, 'drop_index', lambda *args, **kwargs: events.append(('drop',args,kwargs)))
    migration.upgrade(); migration.downgrade()
    assert migration.down_revision == 'd2804c8b39a1'
    assert events[0] == events[2] == 'autocommit'
    assert events[1][2]['postgresql_concurrently'] is True
    assert events[1][2]['postgresql_include'] == ['id']
    assert events[3][2]['postgresql_concurrently'] is True
