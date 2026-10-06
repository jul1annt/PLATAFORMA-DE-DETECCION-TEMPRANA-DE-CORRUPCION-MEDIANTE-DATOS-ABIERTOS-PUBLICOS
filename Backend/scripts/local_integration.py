"""Run the separately provisioned local integration release, with guarded stop."""
import argparse
import ctypes
import hashlib
import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen

COMPONENTS = ('api', 'frontend', 'worker')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def atomic_json(path, value):
    temporary = path.with_suffix('.partial')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def inside(root, path):
    result = Path(path).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError('La ruta no pertenece a la integración')
    return result


def process_stamp(pid):
    if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1:
        return None
    if os.name != 'nt':
        try:
            return Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()[19]
        except (OSError, IndexError):
            return None
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        code = ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:
            return None
        times = [(ctypes.c_ulong * 2)() for _ in range(4)]
        kernel.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.c_void_p] * 4
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
            return None
        return str(times[0][0] | (times[0][1] << 32))
    finally:
        kernel.CloseHandle(handle)


def alive(record):
    return record and record.get('stamp') is not None and process_stamp(record.get('pid')) == record['stamp']


def verify_files(directory, files):
    if not files:
        raise RuntimeError('El manifiesto de archivos está vacío')
    for item in files:
        path = inside(directory, directory / item['path'])
        if path.stat().st_size != item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise RuntimeError('Un archivo del artefacto no coincide con su manifiesto')


def configuration(root):
    from dotenv import dotenv_values
    release, runtime = read_json(root / 'release.json'), read_json(root / 'runtime.json')
    provision = read_json(root / 'provision.json')
    if provision['stage'] != 'provisioned':
        raise RuntimeError('La preparación de la base todavía no terminó')
    backend = inside(root / 'releases', release['backend'])
    frontend = inside(root / 'releases', release['frontend'])
    python = inside(root / 'runtime', runtime['python'])
    env = os.environ.copy()
    env.update({key: value for key, value in dotenv_values(root / 'runtime.env').items() if value is not None})
    if (env.get('DB_HOST'), env.get('DB_PORT'), env.get('DB_NAME')) != ('127.0.0.1', '5433', 'plataforma_integracion_local'):
        raise RuntimeError('La identidad de la integración no coincide')
    if hashlib.sha256((backend / 'requirements.lock').read_bytes()).hexdigest() != runtime['requirements_lock_sha256']:
        raise RuntimeError('El entorno no corresponde al archivo de dependencias')
    base_python = inside(root / 'runtime', runtime['base_python'])
    if hashlib.sha256(base_python.read_bytes()).hexdigest() != runtime['python_executable_sha256']:
        raise RuntimeError('El ejecutable de Python no coincide con su manifiesto')
    bundle = read_json(root / 'frontend-build.json')
    if bundle['ref'] != release.get('frontend_source_ref', release['ref']) or bundle['api_url'] != release['api_url']:
        raise RuntimeError('La interfaz no corresponde a la versión y API seleccionadas')
    verify_files(frontend / 'dist', bundle['files'])
    return release, backend, frontend, python, env


def active_jobs(root):
    from dotenv import dotenv_values
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL
    values = dotenv_values(root / 'runtime.env')
    url = URL.create('postgresql', username=values['DB_USER'], password=values['DB_PASSWORD'],
                     host=values['DB_HOST'], port=int(values['DB_PORT']), database=values['DB_NAME'])
    engine = create_engine(url)
    try:
        with engine.connect() as db:
            db.execute(text('SET TRANSACTION READ ONLY'))
            if tuple(db.execute(text('SELECT current_database(),inet_server_port()')).one()) != ('plataforma_integracion_local', 5433):
                raise RuntimeError('El destino de control no coincide')
            return db.execute(text('SELECT count(*) FROM background_jobs WHERE active')).scalar_one()
    finally:
        engine.dispose()


def frontend_handler(directory):
    directory = directory.resolve()
    class FrontendHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def send_head(self):
            path = unquote(urlsplit(self.path).path)
            candidate = (directory / path.lstrip('/')).resolve()
            if not candidate.is_relative_to(directory):
                self.send_error(404); return None
            if not candidate.is_file():
                if Path(path).suffix:
                    self.send_error(404); return None
                self.path = '/index.html'
            return super().send_head()

        def end_headers(self):
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-store' if self.path == '/index.html' else 'no-cache')
            super().end_headers()

        def log_message(self, format, *args):
            logging.info('Frontend %s', self.command)
    return FrontendHandler


def component(root, name):
    _release, backend, frontend, _python, _env = configuration(root)
    sys.path.insert(0, str(backend))
    os.chdir(backend)
    stop = root / f'stop-{name}'
    if name == 'api':
        import uvicorn
        server = uvicorn.Server(uvicorn.Config('main:app', host='127.0.0.1', port=8000,
                                               access_log=False, log_level='info'))
        def stop_api():
            while not stop.exists():
                time.sleep(.3)
            server.should_exit = True
        threading.Thread(target=stop_api, daemon=True).start()
        server.run()
    elif name == 'worker':
        from core.scheduler import iniciar_scheduler, scheduler
        iniciar_scheduler()
        (root / 'worker-ready').touch()
        try:
            while not stop.exists():
                time.sleep(.3)
        finally:
            if scheduler.running:
                scheduler.shutdown(wait=True)
            (root / 'worker-ready').unlink(missing_ok=True)
    else:
        directory = frontend / 'dist'
        server = ThreadingHTTPServer(('127.0.0.1', 4173), frontend_handler(directory))
        server.timeout = .3
        try:
            while not stop.exists():
                server.handle_request()
        finally:
            server.server_close()


def supervise(root):
    release, _backend, _frontend, python, env = configuration(root)
    state_path, lock_path = root / 'services.json', root / 'supervisor.lock'
    descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(descriptor)
    children, outputs = {}, []
    state = {'phase': 'starting', 'release': release['ref'], 'pid': os.getpid(),
             'stamp': process_stamp(os.getpid()), 'started_at_utc': datetime.now(timezone.utc).isoformat(),
             'controller_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'components': {}}
    try:
        for name in COMPONENTS:
            (root / f'stop-{name}').unlink(missing_ok=True)
        (root / 'worker-ready').unlink(missing_ok=True)
        (root / 'stop-all').unlink(missing_ok=True)
        atomic_json(state_path, state)
        logs = root / 'logs'; logs.mkdir(exist_ok=True)
        for name in COMPONENTS:
            output = (logs / f'{name}.log').open('a', encoding='utf-8')
            outputs.append(output)
            child = subprocess.Popen([str(python), str(Path(__file__).resolve()), '--root', str(root), 'component', name],
                                     cwd=root, env=env, stdout=output, stderr=output,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            children[name] = child
            state['components'][name] = {'pid': child.pid, 'stamp': process_stamp(child.pid)}
        ready = False
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if any(child.poll() is not None for child in children.values()):
                raise RuntimeError('Un componente terminó antes de estar disponible')
            try:
                with urlopen('http://127.0.0.1:8000/openapi.json', timeout=2) as response:
                    api_ready = response.status == 200
                with urlopen('http://127.0.0.1:4173/index.html', timeout=2) as response:
                    frontend_ready = response.status == 200
                ready = api_ready and frontend_ready and (root / 'worker-ready').exists()
                if ready:
                    break
            except OSError:
                pass
            time.sleep(.5)
        if not ready:
            raise RuntimeError('No se confirmó disponibilidad de los tres componentes')
        state['phase'] = 'running'; atomic_json(state_path, state)
        while not (root / 'stop-all').exists():
            if any(child.poll() is not None for child in children.values()):
                raise RuntimeError('Un componente terminó inesperadamente')
            time.sleep(.5)
    except Exception as exc:
        state.update(phase='error', error_type=type(exc).__name__, error_reference=str(uuid.uuid4()))
        atomic_json(state_path, state)
    finally:
        for name in COMPONENTS:
            (root / f'stop-{name}').touch()
        for child in children.values():
            child.wait()  # Drain SQL/jobs; never forcibly kill a different process.
        state.update(phase='stopped', stopped_at_utc=datetime.now(timezone.utc).isoformat())
        atomic_json(state_path, state)
        for output in outputs:
            output.close()
        lock_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1] / '.codex-integration-postgres')
    parser.add_argument('action', choices=('start', 'stop', 'status', 'supervise', 'component'))
    parser.add_argument('component_name', nargs='?', choices=COMPONENTS)
    args = parser.parse_args(); root = args.root.resolve()
    if args.action == 'component':
        if args.component_name is None:
            parser.error('Falta el componente')
        component(root, args.component_name); return
    if args.action == 'supervise':
        supervise(root); return
    state_path = root / 'services.json'
    state = read_json(state_path) if state_path.exists() else {}
    if args.action == 'status':
        print(json.dumps({'phase': state.get('phase', 'not_started'), 'supervisor_alive': bool(alive(state)),
                          'components': {name: bool(alive(item)) for name, item in state.get('components', {}).items()},
                          'release': state.get('release')})); return
    if args.action == 'stop':
        if not alive(state):
            raise RuntimeError('El supervisor registrado no está activo')
        if active_jobs(root):
            raise RuntimeError('Hay trabajos activos; espera a que terminen antes de detener')
        (root / 'stop-all').touch()
        print('Detención solicitada; los servicios cerrarán de forma ordenada'); return
    configuration(root)
    if alive(state) or any(alive(item) for item in state.get('components', {}).values()):
        raise RuntimeError('La integración ya tiene procesos activos')
    if (root / 'supervisor.lock').exists():
        raise RuntimeError('Existe un bloqueo anterior; verifica el estado antes de recuperarlo')
    for port in (8000, 4173):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
    python = inside(root / 'runtime', read_json(root / 'runtime.json')['python'])
    with (root / 'logs-supervisor.log').open('a', encoding='utf-8') as output:
        subprocess.Popen([str(python), str(Path(__file__).resolve()), '--root', str(root), 'supervise'],
                         cwd=root, stdout=output, stderr=output,
                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    print('Inicio solicitado; consulta el estado antes de abrir la plataforma')


if __name__ == '__main__':
    main()
