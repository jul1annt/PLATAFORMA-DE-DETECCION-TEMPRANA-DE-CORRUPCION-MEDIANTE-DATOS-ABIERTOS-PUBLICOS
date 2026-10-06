import http.client
import hashlib
import os
import threading
from http.server import ThreadingHTTPServer

import pytest

from scripts.local_integration import alive, frontend_handler, inside, process_stamp, verify_files


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
