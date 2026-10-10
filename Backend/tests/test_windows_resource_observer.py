import os
from pathlib import Path

import pytest

from scripts.windows_resource_observer import descendants, validate_tree, qualified_tree, WindowsObserver


def records():
    return {10: {'parent_pid': 1, 'name': 'root'},
            11: {'parent_pid': 10, 'name': 'child'},
            12: {'parent_pid': 11, 'name': 'grandchild'},
            30: {'parent_pid': 2, 'name': 'other-cluster'}}


def readings():
    return {pid: {'pid': pid, 'stamp': str(pid), 'available': True} for pid in (10, 11, 12)}


def test_forest_includes_descendants_and_excludes_other_cluster():
    assert descendants(records(), 10) == {10, 11, 12}
    assert descendants(records(), 30) == {30}
    result = validate_tree(records(), readings(), {'pid': 10, 'stamp': '10'})
    assert [r['pid'] for r in result] == [10, 11, 12]
    assert result[-1]['parent_pid'] == 11


@pytest.mark.parametrize('root', [True, 0, -1, '10', 99])
def test_invalid_or_missing_roots_are_rejected(root):
    with pytest.raises(RuntimeError):
        descendants(records(), root)


def test_reused_root_or_parent_cannot_attribute_an_unrelated_child():
    with pytest.raises(RuntimeError):
        validate_tree(records(), readings(), {'pid': 10, 'stamp': 'wrong'})
    measured = readings(); measured[11]['stamp'] = '9'
    with pytest.raises(RuntimeError):
        validate_tree(records(), measured, {'pid': 10, 'stamp': '10'})


def test_stale_parent_links_exclude_the_unrelated_branch_and_record_it():
    measured = readings(); measured[11]['stamp'] = '9'
    accepted, exclusions = qualified_tree(records(), measured, {'pid': 10, 'stamp': '10'})
    assert [r['pid'] for r in accepted] == [10]
    assert exclusions['excluded_pids'] == [11, 12]
    assert exclusions['parent_links'] == [{'pid': 11, 'parent_pid': 10, 'stamp': '9', 'parent_stamp': '10'}]
    with pytest.raises(RuntimeError, match='identidad'):
        qualified_tree(records(), measured, {'pid': 10, 'stamp': 'wrong'})


def test_missing_unavailable_and_extra_processes_cannot_count_as_complete():
    for changed in ({10: readings()[10]}, readings()):
        if len(changed) == 3:
            changed[12]['available'] = False
        with pytest.raises(RuntimeError):
            validate_tree(records(), changed, {'pid': 10, 'stamp': '10'})
    measured = readings(); measured[30] = {'pid': 30, 'stamp': '30', 'available': True}
    with pytest.raises(RuntimeError):
        validate_tree(records(), measured, {'pid': 10, 'stamp': '10'})


@pytest.mark.parametrize('change', ['new_child', 'reused_child'])
def test_inventory_churn_during_sampling_is_rejected(monkeypatch, change):
    observer = WindowsObserver.__new__(WindowsObserver)
    first = records(); second = records()
    if change == 'new_child':
        second[13] = {'parent_pid': 10, 'name': 'new'}
    inventories = iter([first, second])
    calls = {}
    monkeypatch.setattr(observer, 'inventory', lambda: next(inventories))

    def process(pid):
        calls[pid] = calls.get(pid, 0) + 1
        stamp = pid + (100 if change == 'reused_child' and pid == 12 and calls[pid] == 2 else 0)
        return {'pid': pid, 'available': True, 'stamp': str(stamp)}

    monkeypatch.setattr(observer, 'process', process)
    with pytest.raises(RuntimeError, match='árbol cambió'):
        observer.sample({'application': {'pid': 10, 'stamp': '10'}}, Path.cwd())


def test_native_observer_reads_current_process_or_rejects_other_platform():
    if os.name != 'nt':
        with pytest.raises(RuntimeError, match='Windows'):
            WindowsObserver()
        return
    observer = WindowsObserver(); measured = observer.process(os.getpid())
    assert measured['available'] and measured['private_bytes'] > 0
    result = observer.sample({'generator': measured}, Path.cwd())
    assert result['process_inventory_stable']
    assert any(r['pid'] == os.getpid() for r in result['groups']['generator'])
    assert result['available_physical_bytes'] > 0
    assert not observer.process(True)['available']


def test_retries_record_discarded_churn_and_only_return_a_stable_sample(monkeypatch):
    observer = WindowsObserver.__new__(WindowsObserver)
    calls = []

    def sample(*args):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError('El árbol cambió durante la muestra; no se acredita cobertura')
        return {'process_inventory_stable': True}

    monkeypatch.setattr(observer, 'sample', sample)
    result = observer.sample_with_retries({}, Path.cwd())
    assert result['sampling_attempts'] == 2 and len(result['discarded_attempts']) == 1
    assert result['process_inventory_stable']


def test_retries_are_bounded_and_do_not_hide_identity_failure(monkeypatch):
    observer = WindowsObserver.__new__(WindowsObserver)
    calls = []

    def sample(*args):
        calls.append(1)
        raise RuntimeError('Faltan lecturas del árbol de procesos')

    monkeypatch.setattr(observer, 'sample', sample)
    with pytest.raises(RuntimeError):
        observer.sample_with_retries({}, Path.cwd(), max_attempts=2)
    assert len(calls) == 2

    def invalid(*args):
        calls.append(1)
        raise RuntimeError('La identidad de la raíz cambió')

    monkeypatch.setattr(observer, 'sample', invalid)
    with pytest.raises(RuntimeError, match='identidad'):
        observer.sample_with_retries({}, Path.cwd())
    assert len(calls) == 3
    for value in (True, 0, 9):
        with pytest.raises(ValueError):
            observer.sample_with_retries({}, Path.cwd(), max_attempts=value)
