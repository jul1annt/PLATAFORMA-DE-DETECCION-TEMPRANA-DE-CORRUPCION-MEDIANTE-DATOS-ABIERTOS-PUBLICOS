"""Bound a child command and its process tree, without model dependencies."""
import os
import math
import signal
import subprocess


def make_windows_job():
    from .windows_job import WindowsJob
    return WindowsJob()


def terminate_tree(process):
    """Terminate the private POSIX session; Windows uses its owned job handle."""
    try:os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError:pass


def bounded_run(command,*,cwd,env,timeout):
    if not isinstance(timeout,(int,float)) or isinstance(timeout,bool) or not math.isfinite(timeout) or timeout<=0:
        raise ValueError('Tiempo máximo analítico inválido')
    job=make_windows_job() if os.name=='nt' else None
    try:
        process=subprocess.Popen(command,cwd=cwd,env=env,stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|(0x4 if job else 0),start_new_session=os.name!='nt')
        if job:
            try:job.assign_and_resume(process)
            except BaseException:
                # No user code has run if assignment failed. Refuse an
                # unsupervised fallback and reap the owned suspended child.
                process.kill();process.wait(timeout=15)
                for stream in (process.stdin,process.stdout,process.stderr):
                    if stream:stream.close()
                raise
        try:
            stdout,stderr=process.communicate(timeout=timeout)
        except BaseException as original:
            try:
                job.terminate() if job else terminate_tree(process)
                stdout,stderr=process.communicate(timeout=15)
            except BaseException as cleanup_error:
                if process.poll() is None:process.kill()
                raise RuntimeError(f'Cierre analítico incompleto; revisar PID {process.pid}') from cleanup_error
            if isinstance(original,subprocess.TimeoutExpired):
                original.output=stdout;original.stderr=stderr
            raise
        return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
    finally:
        if job:job.close()
