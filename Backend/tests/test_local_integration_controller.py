import http.client
import asyncio
import hashlib
import os
import json
from pathlib import Path
import threading
from http.server import ThreadingHTTPServer

import pytest

from scripts.local_integration import alive, frontend_handler, inside, process_stamp, verify_files, validate_database_identity, observe_disconnects, database_binding
from scripts.local_integration import local_endpoints
from scripts.local_integration import atomic_json


def test_atomic_state_retries_temporary_windows_reader_conflicts(tmp_path, monkeypatch):
    target = tmp_path / 'services.json'
    target.write_text('{"phase":"previous"}')
    original_replace = Path.replace
    attempts = []
    pauses = []

    def replace(path, destination):
        attempts.append(path)
        assert json.loads(target.read_text()) == {'phase': 'previous'}
        if len(attempts) < 3:
            raise PermissionError('simulated sharing violation')
        return original_replace(path, destination)

    monkeypatch.setattr(Path, 'replace', replace)
    monkeypatch.setattr('scripts.local_integration.time.sleep', pauses.append)
    atomic_json(target, {'phase': 'running'})
    assert json.loads(target.read_text()) == {'phase': 'running'}
    assert len(attempts) == 3 and pauses == [.05, .05]
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_state_permanent_denial_is_bounded_and_preserves_previous_state(tmp_path, monkeypatch):
    target = tmp_path / 'services.json'
    target.write_text('{"phase":"previous"}')
    attempts = []
    def denied(path, destination):
        attempts.append(path)
        raise PermissionError('simulated permanent denial')
    monkeypatch.setattr(Path, 'replace', denied)
    monkeypatch.setattr('scripts.local_integration.time.sleep', lambda _: None)
    with pytest.raises(PermissionError):
        atomic_json(target, {'phase': 'running'})
    assert len(attempts) == 20
    assert json.loads(target.read_text()) == {'phase': 'previous'}
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_state_other_io_failures_are_not_retried(tmp_path, monkeypatch):
    target = tmp_path / 'services.json'
    target.write_text('{"phase":"previous"}')
    def broken(path, destination):
        raise OSError('simulated non-transient failure')
    monkeypatch.setattr(Path, 'replace', broken)
    monkeypatch.setattr('scripts.local_integration.time.sleep', lambda _: pytest.fail('Unexpected retry'))
    with pytest.raises(OSError):
        atomic_json(target, {'phase': 'running'})
    assert json.loads(target.read_text()) == {'phase': 'previous'}
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize('api_port,frontend_port', [(8000, 4173), (18100, 14173)])
def test_release_endpoints_preserve_original_ports_and_allow_isolated_packages(api_port, frontend_port):
    assert local_endpoints({'api_url': f'http://127.0.0.1:{api_port}',
                            'frontend_url': f'http://127.0.0.1:{frontend_port}/'}) == {
        'api': {'port': api_port, 'url': f'http://127.0.0.1:{api_port}'},
        'frontend': {'port': frontend_port, 'url': f'http://127.0.0.1:{frontend_port}'},
    }


@pytest.mark.parametrize('bad_url', [None, 18100, '', 'http://127.0.0.1',
    'http://127.0.0.1:80', 'http://127.0.0.1:65536', 'http://127.0.0.1:invalid',
    'https://127.0.0.1:18100', 'http://localhost:18100', 'http://0.0.0.0:18100',
    'http://example.com:18100', 'http://user:password@127.0.0.1:18100',
    'http://127.0.0.1:18100/api', 'http://127.0.0.1:18100/?secret=value',
    'http://127.0.0.1:18100/#fragment', ' http://127.0.0.1:18100',
    'http://127.0.0.1:\n18100'])
def test_release_endpoints_reject_ambiguous_or_external_addresses(bad_url):
    with pytest.raises(RuntimeError):
        local_endpoints({'api_url': bad_url, 'frontend_url': 'http://127.0.0.1:14173'})


def test_release_endpoints_require_both_distinct_components():
    with pytest.raises(RuntimeError):
        local_endpoints({'api_url': 'http://127.0.0.1:18100'})
    with pytest.raises(RuntimeError):
        local_endpoints({'api_url': 'http://127.0.0.1:18100',
                         'frontend_url': 'http://127.0.0.1:18100'})


def test_owned_process_requires_the_original_creation_stamp():
    stamp = process_stamp(os.getpid())
    assert stamp is not None
    assert alive({'pid': os.getpid(), 'stamp': stamp})
    assert not alive({'pid': os.getpid(), 'stamp': 'wrong-stamp'})
    assert process_stamp(True) is None
    assert process_stamp(-1) is None


def test_integration_paths_cannot_escape_their_root(tmp_path):
    root = tmp_path / 'integration'; root.mkdir()
    assert inside(root, root / 'release') == root / 'release'
    with pytest.raises(ValueError):
        inside(root, root / '..' / 'runtime.env')


def test_artifact_integrity_rejects_modified_and_external_files(tmp_path):
    directory = tmp_path / 'dist'; directory.mkdir()
    asset = directory / 'app.js'; asset.write_bytes(b'original')
    item = {'path': 'app.js', 'bytes': 8, 'sha256': hashlib.sha256(b'original').hexdigest()}
    verify_files(directory, [item])
    asset.write_bytes(b'modified')
    with pytest.raises(RuntimeError):
        verify_files(directory, [item])
    with pytest.raises(ValueError):
        verify_files(directory, [dict(item, path='../outside.js')])
    with pytest.raises(RuntimeError):
        verify_files(directory, [])


def test_database_identity_checks_role_oid_schema_and_privileges():
    provision = {'target_database_oid': 123, 'source_revision':'source', 'deployed_revision':'deployed'}
    expected = ('plataforma_integracion_local',5433,'plataforma_integracion',123,'deployed')
    flags = dict.fromkeys(('rolsuper','rolcreatedb','rolcreaterole','rolreplication'),False)
    validate_database_identity(expected, flags, provision)
    for position, replacement in ((0,'plataformaanticorrupcion'),(1,5432),(2,'postgres'),(3,124),(4,'source')):
        changed = list(expected); changed[position] = replacement
        with pytest.raises(RuntimeError):
            validate_database_identity(tuple(changed), flags, provision)
    for flag in flags:
        with pytest.raises(RuntimeError):
            validate_database_identity(expected, dict(flags, **{flag:True}), provision)
    with pytest.raises(RuntimeError):
        validate_database_identity(expected, {}, provision)


def test_declared_operational_target_pins_port_role_oid_and_revision():
    provision = {'target_database': 'plataformaanticorrupcion', 'port': 5432,
                 'app_role': 'plataforma_operacion', 'target_database_oid': 456,
                 'source_revision': 'source', 'deployed_revision': 'deployed'}
    expected = ('plataformaanticorrupcion', 5432, 'plataforma_operacion', 456, 'deployed')
    flags = dict.fromkeys(('rolsuper', 'rolcreatedb', 'rolcreaterole', 'rolreplication'), False)
    validate_database_identity(expected, flags, provision)
    for position, replacement in ((0, 'plataforma_integracion_local'), (1, 5433),
                                  (2, 'postgres'), (3, 123), (4, 'source')):
        changed = list(expected); changed[position] = replacement
        with pytest.raises(RuntimeError):
            validate_database_identity(tuple(changed), flags, provision)
    with pytest.raises(RuntimeError):
        validate_database_identity(expected, dict(flags, rolsuper=True), provision)


def test_risk_acceptance_target_remains_pinned_to_its_isolated_identity():
    provision = {'target_database': 'codex_risk_engine_20261016_test', 'port': 5433,
                 'app_role': 'plataforma_integracion', 'target_database_oid': 82244,
                 'source_revision': 'f67b120ce841'}
    expected = ('codex_risk_engine_20261016_test', 5433, 'plataforma_integracion',
                82244, 'f67b120ce841')
    flags = dict.fromkeys(('rolsuper', 'rolcreatedb', 'rolcreaterole', 'rolreplication'), False)
    validate_database_identity(expected, flags, provision)
    for position, replacement in ((0, 'plataformaanticorrupcion'), (1, 5432),
                                  (2, 'plataforma_operacion'), (3, 24577)):
        changed = list(expected); changed[position] = replacement
        with pytest.raises(RuntimeError):
            validate_database_identity(tuple(changed), flags, provision)


def test_database_binding_rejects_unknown_crossed_and_untyped_targets():
    for database, port, role in (
        ('plataformaanticorrupcion', 5433, 'plataforma_operacion'),
        ('plataforma_integracion_local', 5432, 'plataforma_integracion'),
        ('unrelated', 5432, 'plataforma_operacion'),
        ('plataformaanticorrupcion', '5432', 'plataforma_operacion'),
        ('plataformaanticorrupcion', 5432.0, 'plataforma_operacion'),
        ('plataformaanticorrupcion', 5432, 'postgres'),
    ):
        with pytest.raises(RuntimeError):
            database_binding({'target_database': database, 'port': port, 'app_role': role})


def test_database_identity_rejects_boolean_and_nonpositive_oids():
    flags = dict.fromkeys(('rolsuper', 'rolcreatedb', 'rolcreaterole', 'rolreplication'), False)
    for oid in (True, 0, -1, '123'):
        provision = {'target_database_oid': oid, 'source_revision': 'source'}
        with pytest.raises(RuntimeError):
            validate_database_identity(('plataforma_integracion_local', 5433,
                                        'plataforma_integracion', oid, 'source'), flags, provision)


def test_optional_http_trace_forwards_body_and_never_records_secrets(tmp_path):
    async def exercise():
        incoming = asyncio.Queue(); release = asyncio.Event(); body_received = asyncio.Event()
        body = {'type':'http.request','body':b'private-body','more_body':False}
        await incoming.put(body)
        async def application(scope, receive, send):
            assert await receive() == body
            body_received.set()
            await release.wait()
            await send({'type':'http.response.start','status':200,'headers':[]})
        sent = []
        async def send(message): sent.append(message)
        audit = tmp_path/'disconnect.jsonl'
        wrapped = observe_disconnects(application,audit)
        task = asyncio.create_task(wrapped({'type':'http','method':'GET','path':'/api/procesados/search',
                                           'query_string':b'password=private-query',
                                           'headers':[(b'authorization',b'private-token')]},incoming.get,send))
        await body_received.wait()
        await incoming.put({'type':'http.disconnect'})
        for _ in range(100):
            if audit.exists(): break
            await asyncio.sleep(.001)
        text = audit.read_text()
        assert 'http.disconnect' in text and '/api/procesados/search' in text
        assert 'private-' not in text and 'authorization' not in text
        release.set(); await task
        assert sent[0]['status'] == 200
    asyncio.run(exercise())


def test_optional_http_trace_preserves_lifespan_scope(tmp_path):
    async def application(scope, receive, send):
        return scope['type']
    assert asyncio.run(observe_disconnects(application,tmp_path/'unused.jsonl')(
        {'type':'lifespan'},None,None)) == 'lifespan'
    assert not (tmp_path/'unused.jsonl').exists()


def test_spa_routes_and_assets_never_expose_parent_credentials(tmp_path):
    directory = tmp_path / 'dist'; directory.mkdir()
    (directory / 'index.html').write_text('<html>Integration</html>', encoding='utf-8')
    (directory / 'app.js').write_text('console.log("integration")', encoding='utf-8')
    (tmp_path / 'runtime.env').write_text('PRIVATE=never-serve-this', encoding='utf-8')
    server = ThreadingHTTPServer(('127.0.0.1', 0), frontend_handler(directory))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        for route, status in (('/admin/login', 200), ('/contratos?offset=20', 200),
                              ('/app.js', 200), ('/missing.js', 404),
                              ('/%2e%2e/runtime.env', 404), ('/runtime.env', 404)):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            try:
                connection.request('GET', route)
                response = connection.getresponse(); body = response.read()
                assert response.status == status
                assert b'never-serve-this' not in body
                assert response.getheader('X-Content-Type-Options') == 'nosniff'
            finally:
                connection.close()
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
