"""The startup gate checks the interpreter which will actually infer."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from analytics_ml.runtime import prediction_code_sha256
from scripts.risk_runtime_check import check_inference_environment


BACKEND = Path(__file__).resolve().parents[1]


def reports(tmp_path):
    base = str(tmp_path / 'base')
    common = {'base_prefix': base, 'isolated': 1,
              'prediction_code_sha256': prediction_code_sha256(),
              'training_dependencies_loaded': False}
    return [{**common, 'prefix': str(tmp_path / 'api')},
            {**common, 'prefix': str(tmp_path / 'inference')}]


def simulated(monkeypatch, tmp_path, entries):
    interpreter = tmp_path / 'inference-python.exe'
    interpreter.write_bytes(b'not executed: mocked process runner')
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        value = entries.pop(0)
        return value if isinstance(value, subprocess.CompletedProcess) else subprocess.CompletedProcess(command, 0, json.dumps(value), '')

    monkeypatch.setattr('modules.motor_riesgo.process_runner.bounded_run', run)
    return interpreter, calls


def test_probe_is_bounded_isolated_and_has_no_database_credentials(monkeypatch, tmp_path):
    interpreter, calls = simulated(monkeypatch, tmp_path, reports(tmp_path))
    environment = {'RISK_INFERENCE_PYTHON': str(interpreter), 'DB_PASSWORD': 'test-secret',
                   'SECRET_KEY': 'test-secret', 'ENCRYPTION_KEY': 'test-secret',
                   'DATABASE_URL': 'test-secret', 'TEST_DATABASE_URL': 'test-secret',
                   'PATH': os.environ.get('PATH', '')}
    result = check_inference_environment(BACKEND, Path(sys.executable), environment)
    assert result['separate_api_environment'] is True
    assert len(calls) == 2
    for command, options in calls:
        assert command[1:] == ['-I', str(BACKEND / 'scripts/risk_inference_probe.py')]
        assert options['timeout'] == 30 and options['cwd'] == BACKEND
        assert not any(key.startswith(('DB_', 'SECRET_', 'ENCRYPTION_')) for key in options['env'])
        assert 'DATABASE_URL' not in options['env'] and 'TEST_DATABASE_URL' not in options['env']
        assert options['env']['OPENBLAS_NUM_THREADS'] == '1'
    assert environment['DB_PASSWORD'] == 'test-secret'


@pytest.mark.parametrize('change', ['same_api_prefix', 'base_runtime', 'changed_code',
                                    'training_dependency', 'not_isolated', 'missing_field',
                                    'relative_prefix'])
def test_incompatible_inference_runtime_cannot_approve_startup(monkeypatch, tmp_path, change):
    entries = reports(tmp_path)
    if change == 'same_api_prefix':
        entries[1]['prefix'] = entries[0]['prefix']
    elif change == 'base_runtime':
        entries[1]['prefix'] = entries[1]['base_prefix']
    elif change == 'changed_code':
        entries[1]['prediction_code_sha256'] = {'different': 'a' * 64}
    elif change == 'training_dependency':
        entries[1]['training_dependencies_loaded'] = True
    elif change == 'not_isolated':
        entries[1]['isolated'] = 0
    elif change == 'missing_field':
        del entries[1]['prefix']
    else:
        entries[1]['prefix'] = 'relative'
    interpreter, _ = simulated(monkeypatch, tmp_path, entries)
    with pytest.raises(ValueError):
        check_inference_environment(BACKEND, Path(sys.executable), {'RISK_INFERENCE_PYTHON': str(interpreter)})


@pytest.mark.parametrize('stdout,code', [('not-json', 0), ('{}', 0), ('', 1)])
def test_invalid_or_failed_probe_is_rejected(monkeypatch, tmp_path, stdout, code):
    entries = [subprocess.CompletedProcess([], code, stdout, 'private diagnostic')]
    interpreter, _ = simulated(monkeypatch, tmp_path, entries)
    with pytest.raises(ValueError) as error:
        check_inference_environment(BACKEND, Path(sys.executable), {'RISK_INFERENCE_PYTHON': str(interpreter)})
    assert 'private diagnostic' not in str(error.value)


@pytest.mark.parametrize('configured', ['', 'relative-python', 'C:/nonexistent-preflight-runtime/python.exe'])
def test_missing_interpreter_fails_before_launch(monkeypatch, configured):
    def unexpected(*args, **kwargs):
        pytest.fail('No process should be started')
    monkeypatch.setattr('modules.motor_riesgo.process_runner.bounded_run', unexpected)
    with pytest.raises(ValueError):
        check_inference_environment(BACKEND, Path(sys.executable), {'RISK_INFERENCE_PYTHON': configured})


def test_real_inference_virtual_environment_loads_only_pure_prediction_code():
    interpreter = os.environ.get('TEST_ML_INFERENCE_PYTHON')
    if not interpreter or not Path(interpreter).is_file():
        pytest.skip('Independent inference interpreter is not configured')
    environment = dict(os.environ, RISK_INFERENCE_PYTHON=interpreter)
    result = check_inference_environment(BACKEND, Path(sys.executable), environment)
    assert result == {'isolated': True, 'separate_api_environment': True,
                      'training_dependencies_loaded': False,
                      'prediction_code_sha256': prediction_code_sha256()}


def test_real_api_interpreter_cannot_be_reused_for_inference():
    with pytest.raises(ValueError, match='separado de la API'):
        check_inference_environment(BACKEND, Path(sys.executable),
                                    dict(os.environ, RISK_INFERENCE_PYTHON=sys.executable))
