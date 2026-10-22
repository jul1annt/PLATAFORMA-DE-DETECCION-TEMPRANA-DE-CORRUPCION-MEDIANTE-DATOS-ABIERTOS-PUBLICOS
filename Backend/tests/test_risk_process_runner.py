"""Process ownership, thread limits and failed cleanup are explicit."""
import subprocess
import json
from types import SimpleNamespace
import pytest
from modules.motor_riesgo import process_runner as runner


class Child:
    pid=54321
    returncode=0
    def __init__(self,steps):self.steps=list(steps);self.killed=False
    def communicate(self,timeout):
        item=self.steps.pop(0)
        if isinstance(item,BaseException):raise item
        return item
    def poll(self):return None
    def kill(self):self.killed=True


class Job:
    def __init__(self):self.assigned=[];self.terminated=False;self.closed=False
    def assign_and_resume(self,process):self.assigned.append(process.pid)
    def terminate(self):self.terminated=True
    def close(self):self.closed=True


@pytest.fixture(autouse=True)
def owned_jobs(monkeypatch):
    jobs=[]
    def factory():
        job=Job();jobs.append(job);return job
    monkeypatch.setattr(runner,'make_windows_job',factory)
    return jobs


@pytest.mark.parametrize('timeout',[0,-1,True,float('inf'),float('nan'),'10'])
def test_invalid_deadline_never_starts_a_command(monkeypatch,timeout):
    monkeypatch.setattr(runner.subprocess,'Popen',lambda *a,**k:pytest.fail('No process should start'))
    with pytest.raises(ValueError):runner.bounded_run(['owned'],cwd='.',env={},timeout=timeout)


@pytest.mark.parametrize('windows',[False,True])
def test_owned_command_uses_hidden_windows_or_private_posix_session(monkeypatch,windows,owned_jobs):
    child=Child([('stdout','stderr')]);calls=[]
    monkeypatch.setattr(runner,'os',SimpleNamespace(name='nt' if windows else 'posix'))
    monkeypatch.setattr(runner.subprocess,'Popen',lambda command,**kwargs:(calls.append((command,kwargs)) or child))
    result=runner.bounded_run(['owned'],cwd='working',env={'safe':'value'},timeout=10)
    assert (result.returncode,result.stdout,result.stderr)==(0,'stdout','stderr')
    assert calls[0][1]['start_new_session'] is not windows
    assert calls[0][1]['stdin']==subprocess.DEVNULL and calls[0][1]['env']=={'safe':'value'}
    if windows:
        assert calls[0][1]['creationflags'] & 0x4
        assert owned_jobs[0].assigned==[child.pid] and owned_jobs[0].closed
    else:assert owned_jobs==[]


def test_windows_deadline_kills_only_owned_job_then_reaps_output(monkeypatch,tmp_path,owned_jobs):
    original=subprocess.TimeoutExpired(['owned'],1)
    child=Child([original,('partial output','diagnostic')])
    monkeypatch.setattr(runner,'os',SimpleNamespace(name='nt',environ={'SystemRoot':str(tmp_path)}))
    monkeypatch.setattr(runner.subprocess,'Popen',lambda *a,**k:child)
    monkeypatch.setattr(runner.subprocess,'run',lambda *a,**k:pytest.fail('No PID-tree lookup should be needed'))
    with pytest.raises(subprocess.TimeoutExpired) as error:
        runner.bounded_run(['owned'],cwd='.',env={},timeout=1)
    assert owned_jobs[0].assigned==[child.pid] and owned_jobs[0].terminated and owned_jobs[0].closed
    assert error.value.output=='partial output' and error.value.stderr=='diagnostic'


def test_posix_deadline_terminates_private_group(monkeypatch):
    child=Child([subprocess.TimeoutExpired(['owned'],1),('','')]);groups=[]
    monkeypatch.setattr(runner,'os',SimpleNamespace(name='posix',killpg=lambda pid,sig:groups.append((pid,sig))))
    monkeypatch.setattr(runner,'signal',SimpleNamespace(SIGKILL=9))
    monkeypatch.setattr(runner.subprocess,'Popen',lambda *a,**k:child)
    with pytest.raises(subprocess.TimeoutExpired):runner.bounded_run(['owned'],cwd='.',env={},timeout=1)
    assert groups==[(child.pid,runner.signal.SIGKILL)]


def test_failed_cleanup_is_visible_and_does_not_claim_success(monkeypatch):
    child=Child([subprocess.TimeoutExpired(['owned'],1)])
    monkeypatch.setattr(runner.subprocess,'Popen',lambda *a,**k:child)
    monkeypatch.setattr(runner,'os',SimpleNamespace(name='posix'))
    def failed(_process):raise RuntimeError('synthetic cleanup failure')
    monkeypatch.setattr(runner,'terminate_tree',failed)
    with pytest.raises(RuntimeError,match='Cierre analítico incompleto'):
        runner.bounded_run(['owned'],cwd='.',env={},timeout=1)
    assert child.killed


def test_job_creation_failure_never_starts_unprotected_child(monkeypatch):
    monkeypatch.setattr(runner,'os',SimpleNamespace(name='nt'))
    def failed():raise OSError('synthetic job creation failure')
    monkeypatch.setattr(runner,'make_windows_job',failed)
    monkeypatch.setattr(runner.subprocess,'Popen',lambda *a,**k:pytest.fail('No fallback permitted'))
    with pytest.raises(OSError):runner.bounded_run(['owned'],cwd='.',env={},timeout=1)


def test_job_assignment_failure_reaps_suspended_child_without_running(monkeypatch):
    child=Child([]);closed=[];waited=[];job=Job()
    child.stdin=None;child.stdout=SimpleNamespace(close=lambda:closed.append('stdout'));child.stderr=SimpleNamespace(close=lambda:closed.append('stderr'))
    child.wait=lambda timeout:waited.append(timeout)
    def failed(process):raise OSError('synthetic assignment failure')
    job.assign_and_resume=failed
    monkeypatch.setattr(runner,'os',SimpleNamespace(name='nt'))
    monkeypatch.setattr(runner,'make_windows_job',lambda:job)
    monkeypatch.setattr(runner.subprocess,'Popen',lambda *a,**k:child)
    with pytest.raises(OSError):runner.bounded_run(['owned'],cwd='.',env={},timeout=1)
    assert child.killed and waited==[15] and closed==['stdout','stderr'] and job.closed


def test_spawn_failure_releases_job(monkeypatch,owned_jobs):
    monkeypatch.setattr(runner,'os',SimpleNamespace(name='nt'))
    def failed(*a,**k):raise OSError('synthetic launch failure')
    monkeypatch.setattr(runner.subprocess,'Popen',failed)
    with pytest.raises(OSError):runner.bounded_run(['owned'],cwd='.',env={},timeout=1)
    assert owned_jobs[0].closed and not owned_jobs[0].assigned


def test_service_checks_log_destination_before_starting_process(tmp_path,monkeypatch):
    from modules.motor_riesgo import service
    executable=tmp_path/'python.exe';executable.write_bytes(b'NOT EXECUTED')
    root=tmp_path/'risk';root.mkdir();monkeypatch.setattr(service,'work_root',lambda:root)
    monkeypatch.setattr(runner,'bounded_run',lambda *a,**k:pytest.fail('Outside output must never launch'))
    with pytest.raises(ValueError,match='fuera del directorio'):
        service.run_process(str(executable),['infer','--output',str(tmp_path/'outside.json')])


def test_service_strips_credentials_limits_threads_and_logs_deadline(tmp_path,monkeypatch):
    from modules.motor_riesgo import service
    executable=tmp_path/'python.exe';executable.write_bytes(b'NOT EXECUTED')
    monkeypatch.setattr(service,'work_root',lambda:tmp_path)
    monkeypatch.setenv('DB_PASSWORD','synthetic-secret');monkeypatch.setenv('SECRET_KEY','synthetic-key')
    def timeout(command,**kwargs):
        environment=kwargs['env']
        assert not any(key.startswith(('DB_','SECRET_','ENCRYPTION_')) for key in environment)
        assert environment['OMP_NUM_THREADS']==environment['OPENBLAS_NUM_THREADS']==environment['MKL_NUM_THREADS']=='1'
        assert environment['PYTHONIOENCODING']=='utf-8' and command[1]=='-I'
        raise subprocess.TimeoutExpired(command,1,output='partial',stderr='diagnostic')
    monkeypatch.setattr(runner,'bounded_run',timeout)
    with pytest.raises(subprocess.TimeoutExpired):service.run_process(str(executable),['infer','--output',str(tmp_path/'output.json')],timeout=1)
    assert 'árbol analítico cerrado' in (tmp_path/'output.process.log').read_text(encoding='utf-8')
    receipt=json.loads((tmp_path/'output.process.execution.json').read_text(encoding='utf-8'))
    assert receipt['scope']=='execution_lifecycle_not_predictive_approval' and receipt['status']=='TIMEOUT_TREE_CLOSED'
    assert receipt['maximum_seconds']==1 and set(receipt['launcher_code_sha256'])=={'service.py','process_runner.py','windows_job.py'}
    assert 'synthetic-secret' not in json.dumps(receipt) and 'synthetic-key' not in json.dumps(receipt)
