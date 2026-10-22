"""Frozen serial batches recover interruption without accepting changed artifacts."""
import hashlib
import json
from pathlib import Path
import pytest
from scripts import risk_rolling_batch as batch
from test_rolling_evidence import frame, row


def manifest(tmp_path, n=2):
    entries = []
    for i in range(n):
        payload = frame(); payload['target']['process_id'] += str(i)
        payload['rows'] = [row('P1'), row('P2'), row('P3')]; payload['scope']['raw_rows'] = 3
        name = f'input-{i}.json'; path = tmp_path / name
        path.write_text(json.dumps(payload), encoding='utf-8')
        entries.append({'path': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps({'version': 'rolling-batch-input-v1', 'inputs': entries}), encoding='utf-8')
    return path


def test_complete_and_identical_reuse(tmp_path):
    source = manifest(tmp_path); output = tmp_path / 'output'
    assert batch.run(source, output)['reused_identical_results'] == 0
    before = {p.name: p.read_bytes() for p in output.glob('*.json')}
    assert batch.run(source, output)['reused_identical_results'] == 2
    assert before == {p.name: p.read_bytes() for p in output.glob('*.json')}
    complete = json.loads((output / 'complete.json').read_text())
    assert complete['concurrency'] == 1 and not complete['publication_authorized']
    assert complete['complete_risk_scores'] == 0


def test_interruption_recovers_completed_result(tmp_path, monkeypatch):
    source = manifest(tmp_path); output = tmp_path / 'output'; original = batch.assess; calls = 0
    def interrupted(payload):
        nonlocal calls
        calls += 1
        if calls == 2: raise RuntimeError('interrupción simulada')
        return original(payload)
    with monkeypatch.context() as patch:
        patch.setattr(batch, 'assess', interrupted)
        with pytest.raises(RuntimeError): batch.run(source, output)
    assert not (output / 'complete.json').exists()
    before = (output / 'result-000000.json').read_bytes()
    assert batch.run(source, output)['reused_identical_results'] == 1
    assert (output / 'result-000000.json').read_bytes() == before


def test_changed_input_detected_before_output_creation(tmp_path):
    source = manifest(tmp_path); output = tmp_path / 'output'
    (tmp_path / 'input-1.json').write_text('{}')
    with pytest.raises(ValueError, match='hash'): batch.run(source, output)
    assert not output.exists()


def test_changed_result_never_overwritten(tmp_path):
    source = manifest(tmp_path); output = tmp_path / 'output'; batch.run(source, output)
    result = output / 'result-000000.json'; result.write_text('{}')
    with pytest.raises(ValueError, match='alterado'): batch.run(source, output)
    assert result.read_text() == '{}'


def test_changed_implementation_cannot_resume(tmp_path, monkeypatch):
    source = manifest(tmp_path); output = tmp_path / 'output'; batch.run(source, output)
    monkeypatch.setattr(batch, 'code_hashes', lambda: {'changed.py': '0' * 64})
    with pytest.raises(ValueError, match='incompatible'): batch.run(source, output)


def test_code_snapshot_replays_without_installed_packages(tmp_path):
    import subprocess
    import sys
    source = manifest(tmp_path); output = tmp_path / 'output'; batch.run(source, output)
    clone = output / 'code/scripts/risk_rolling_batch.py'
    result = subprocess.run([sys.executable, '-I', '-S', str(clone), '--manifest', str(source),
                             '--output-directory', str(tmp_path / 'replay')],
                            cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['results'] == 2
    original = json.loads((output / 'complete.json').read_text())
    replayed = json.loads((tmp_path / 'replay/complete.json').read_text())
    assert original == replayed


@pytest.mark.parametrize('path', ['../outside.json', 'C:/outside.json', 'input-0.json'])
def test_escape_absolute_and_duplicate_inputs_rejected(tmp_path, path):
    source = manifest(tmp_path); data = json.loads(source.read_text()); data['inputs'][1]['path'] = path
    source.write_text(json.dumps(data))
    with pytest.raises(ValueError): batch.run(source, tmp_path / 'output')


def test_live_lock_prevents_second_worker(tmp_path):
    source = manifest(tmp_path); output = tmp_path / 'output'; output.mkdir()
    with batch.batch_lock(output / '.lock'):
        with pytest.raises(OSError): batch.run(source, output)
    assert batch.run(source, output)['results'] == 2


def test_process_exit_releases_lock(tmp_path):
    import os
    import subprocess
    import sys
    source = manifest(tmp_path); output = tmp_path / 'output'; output.mkdir()
    code = ('from pathlib import Path\nfrom scripts.risk_rolling_batch import batch_lock\n'
            'import sys,os\nwith batch_lock(Path(sys.argv[1])):\n print("LOCKED",os.getpid(),flush=True)\n sys.stdin.readline()\n')
    proc = subprocess.Popen([sys.executable, '-u', '-c', code, str(output / '.lock')],
                            cwd=Path(__file__).resolve().parents[1], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    actual_pid = None
    try:
        ready = proc.stdout.readline().strip().split()
        assert len(ready) == 2 and ready[0] == 'LOCKED'
        actual_pid = int(ready[1])
        with pytest.raises(OSError): batch.run(source, output)
    finally:
        # Windows venv launchers can have a different PID from the interpreter
        # holding the lock. Terminate that confirmed child, not only its launcher.
        import signal
        if actual_pid is not None:
            try: os.kill(actual_pid, signal.SIGTERM)
            except ProcessLookupError: pass
        proc.stdin.close()
        proc.wait(timeout=10)
    assert batch.run(source, output)['results'] == 2
