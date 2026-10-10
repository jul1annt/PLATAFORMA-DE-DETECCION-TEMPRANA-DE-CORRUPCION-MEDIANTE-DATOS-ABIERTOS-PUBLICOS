from contextlib import contextmanager
import importlib.util
from pathlib import Path

import pytest


def migration(monkeypatch, states):
    path = Path(__file__).resolve().parents[1] / 'database/migrations/versions/08c6d9a2e4b1_compact_quality_metrics.py'
    spec = importlib.util.spec_from_file_location('compact_migration', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    events = []
    class Context:
        @contextmanager
        def autocommit_block(self):
            events.append('autocommit'); yield
    monkeypatch.setattr(module.op, 'get_context', lambda: Context())
    results = iter(states)
    monkeypatch.setattr(module, '_index', lambda name: next(results))
    monkeypatch.setattr(module.op, 'create_index', lambda *a, **kw: events.append(('create', a, kw)))
    monkeypatch.setattr(module.op, 'drop_index', lambda *a, **kw: events.append(('drop', a, kw)))
    monkeypatch.setattr(module.op, 'execute', lambda sql: events.append(('rename', sql)))
    return module, events


def definition(include=False, **changes):
    return dict(valid=True, ready=True, unique=False, plain=True, method='btree',
                table_schema='public', table_name='contratos_procesados', key_count=4,
                column_count=5 if include else 4,
                columns=['es_incompleto', 'es_sospechoso', 'clasificacion_riesgo', 'nivel_confianza']
                        + (['id'] if include else []), **changes)


def test_upgrade_verifies_replacement_before_dropping_old_index(monkeypatch):
    module, events = migration(monkeypatch, [definition(True), None, definition()])
    module.upgrade()
    assert module.down_revision == 'f4826b9d1c30'
    assert [e[0] for e in events[1:]] == ['create', 'drop', 'rename']
    assert events[1][2]['postgresql_concurrently'] and 'postgresql_include' not in events[1][2]
    assert events[2][2]['postgresql_concurrently']


def test_downgrade_restores_include_coverage_before_dropping_compact_index(monkeypatch):
    module, events = migration(monkeypatch, [definition(), None, definition(True)])
    module.downgrade()
    assert events[1][2]['postgresql_include'] == ['id']
    assert [e[0] for e in events[1:]] == ['create', 'drop', 'rename']


@pytest.mark.parametrize('current', [definition(True), None])
def test_upgrade_resumes_after_create_or_drop_without_rebuilding(monkeypatch, current):
    module, events = migration(monkeypatch, [current, definition()])
    module.upgrade()
    assert not any(e[0] == 'create' for e in events[1:])
    assert any(e[0] == 'drop' for e in events[1:]) == (current is not None)
    assert events[-1][0] == 'rename'


def test_completed_upgrade_is_a_noop(monkeypatch):
    module, events = migration(monkeypatch, [definition(), None])
    module.upgrade(); assert events == ['autocommit']


@pytest.mark.parametrize('field,value', [('valid', False), ('ready', False), ('unique', True),
    ('plain', False), ('method', 'hash'), ('table_name', 'otra'), ('table_schema', 'otra'),
    ('key_count', 3), ('column_count', 5), ('columns', ['id'])])
def test_unverified_replacement_never_drops_the_original(monkeypatch, field, value):
    bad = definition(); bad[field] = value
    module, events = migration(monkeypatch, [definition(True), bad])
    with pytest.raises(RuntimeError, match='reemplazo'):
        module.upgrade()
    assert events == ['autocommit']


def test_unexpected_old_or_leftover_index_is_preserved(monkeypatch):
    bad = definition(True); bad['valid'] = False
    for states in ([bad, None], [definition(), definition()]):
        module, events = migration(monkeypatch, states)
        with pytest.raises(RuntimeError):
            module.upgrade()
        assert events == ['autocommit']
