import http.client
import asyncio
import hashlib
import os
import threading
from http.server import ThreadingHTTPServer

import pytest

from scripts.local_integration import alive, frontend_handler, inside, process_stamp, verify_files, validate_database_identity, observe_disconnects


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
