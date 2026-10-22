"""Real TLS/socket interruption through the SECOP adapter and durable worker."""
import json
import os
import re
import socket
import ssl
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, func
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from urllib3 import HTTPSConnectionPool

from core.database import get_db
from main import app
from modules.auth.model.Admin import Admin
from modules.auth.model.AdminSession import AdminSession
from modules.auth.service.AuthService import AuthService
from modules.ingesta.adapters.secop_adapter import SecopAdapter
from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.ingesta.model.RawSecop import RawSecop
from modules.ingesta.model.RawSecopHistorial import RawSecopHistorial
from modules.ingesta.model.SincronizacionHistorial import EstadoSync, SincronizacionHistorial
from modules.ingesta.services import IngestaService as ingestion_module
from modules.jobs import worker
from modules.jobs.model import BackgroundJob
from modules.jobs.service import enqueue_job
from shared.enums import TipoFormato


def test_tls_body_cut_preserves_checkpoint_and_next_worker_resumes(
    postgres_test_session, monkeypatch, tmp_path,
):
    # The explicit PostgreSQL fixture validates the isolated destination.
    engine = create_engine(make_url(os.environ['TEST_DATABASE_URL']), pool_size=6)
    monkeypatch.setattr(worker, 'SessionLocal', lambda: Session(engine))
    prefix = uuid.uuid4().hex[:12]
    old_watermark = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
    source_id = admin_id = None
    jobs, calls = [], []
    fault_started, release_fault, healthy = threading.Event(), threading.Event(), threading.Event()
    observations = {}

    # Trust only this ephemeral certificate; hostname, SNI and CERT_REQUIRED
    # still apply to every real HTTPS request made by the production adapter.
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'www.datos.gov.co')])
    now = datetime.now(timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                   .public_key(key.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
                   .add_extension(x509.SubjectAlternativeName([x509.DNSName('www.datos.gov.co')]), critical=False)
                   .sign(key, hashes.SHA256()))
    certificate_path, key_path = tmp_path / 'source.pem', tmp_path / 'source-key.pem'
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                         serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()))
    rows = [{':id': f'wire-{index:05d}', 'id_del_proceso': f'wire-{prefix}-{index:05d}',
             'valor_total_adjudicacion': '1.00'} for index in range(10001)]

    class SourceHandler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def do_GET(self):
            query = {key: values[0] for key, values in parse_qs(urlparse(self.path).query).items()}
            match = re.search(r":id > '([^']+)'", query['$where'])
            cursor = match.group(1) if match else None
            broken = cursor == 'wire-04999' and not healthy.is_set()
            calls.append({'cursor': cursor, 'query': query, 'host': self.headers.get('Host'),
                          'body_cut': broken})
            if broken:
                fault_started.set()
                if not release_fault.wait(20):
                    self.close_connection = True
                    return
                # Announce a complete JSON body, send a prefix, then terminate
                # the actual TLS connection. urllib3 must detect IncompleteRead.
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', '10000')
                self.end_headers()
                self.wfile.write(b'[{":id":"wire-05000"'); self.wfile.flush()
                self.close_connection = True
                try:
                    self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                self.connection.close()
                return
            start = 0 if cursor is None else int(cursor.split('-')[1]) + 1
            body = json.dumps(rows[start:start + int(query['$limit'])]).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), SourceHandler)
    server.daemon_threads = True
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(str(certificate_path), str(key_path))
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    class LocalTransportAdapter(SecopAdapter):
        def _pool_for(self, address):
            # Only the test's transport destination changes. Pagination,
            # retries, JSON handling, services and SQL execute unmodified.
            if address not in self._pools:
                self._pools[address] = HTTPSConnectionPool(
                    '127.0.0.1', port=server.server_port, assert_hostname=self.host,
                    server_hostname=self.host, cert_reqs='CERT_REQUIRED',
                    ca_certs=str(certificate_path), retries=False, maxsize=1, block=True)
            return self._pools[address]

    def adapter_factory(_kind, endpoint, _api_key):
        return LocalTransportAdapter(endpoint, pinned_ips=('8.8.8.8',))

    monkeypatch.setattr(ingestion_module, 'get_adapter', adapter_factory)
    monkeypatch.setattr(ingestion_module.settings, 'INGESTA_MAX_RECORDS_PER_SYNC', 20000)

    def api_session():
        with Session(engine) as db:
            yield db

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = api_session
    try:
        with Session(engine) as db:
            source = FuenteDatos(nombre=f'wire-source-{prefix}', tipo='SECOP', formato=TipoFormato.JSON,
                                 endpoint='https://www.datos.gov.co/resource/wire-test.json',
                                 activo=False, ultima_sync=old_watermark)
            admin = Admin(username=f'wire-{prefix}', email=f'wire-{prefix}@example.com',
                          hashed_password='unused-test-hash', is_active=True)
            db.add_all([source, admin]); db.flush()
            source_id, admin_id = source.id, admin.id
            token, jti, expires = AuthService(db).create_access_token(admin.id, admin.username)
            db.add(AdminSession(jti=jti, admin_id=admin.id, expires_at=expires)); db.commit()
            job, created = enqueue_job(db, kind='INGESTA', payload={'fuente_id':source_id},
                                      resource_key=f'ingesta:{source_id}')
            assert created
            jobs.append(job.id); public_id = str(job.public_id)

        with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(worker.process_next_job)
            try:
                assert fault_started.wait(20)
                with Session(engine) as db:
                    first = db.get(BackgroundJob, jobs[0])
                    checkpoint = dict(first.result['checkpoint'])
                    assert first.status == 'EN_PROCESO'
                    assert checkpoint['last_id'] == 'wire-04999' and checkpoint['window_rows'] == 5000
                    assert db.query(RawSecop).filter_by(fuente_id=source_id).count() == 5000
                    duplicate, created = enqueue_job(db, kind='INGESTA', payload={'fuente_id':source_id},
                                                    resource_key=f'ingesta:{source_id}')
                    assert not created and duplicate.id == jobs[0]
                assert worker.recover_abandoned_jobs() == 0
                assert worker.process_next_job() is False
                response = client.get(f'/api/jobs/{public_id}', headers={'Authorization': 'Bearer ' + token})
                assert response.status_code == 200 and response.json()['status'] == 'EN_PROCESO'
                observations['api_during_cut'] = {'http':response.status_code, 'status':response.json()['status']}
            finally:
                release_fault.set()
                assert future.result(timeout=30) is True

            with Session(engine) as db:
                first = db.get(BackgroundJob, jobs[0])
                assert first.status == 'ERROR' and first.active is False and first.attempts == 1
                assert first.result['checkpoint'] == checkpoint
                assert db.get(FuenteDatos, source_id).ultima_sync == old_watermark
                assert db.query(RawSecop).filter_by(fuente_id=source_id).count() == 5000
                assert db.query(RawSecop).filter_by(fuente_id=source_id, socrata_row_id='wire-05000').count() == 0
            cuts = [call for call in calls if call['body_cut']]
            assert len(cuts) == SecopAdapter.MAX_REQUEST_ATTEMPTS == 6
            assert len(calls) == 7 and worker.process_next_job() is False
            healthy.set()
            with Session(engine) as db:
                next_job, created = enqueue_job(db, kind='INGESTA', payload={'fuente_id':source_id},
                                               resource_key=f'ingesta:{source_id}')
                assert created; jobs.append(next_job.id)
            assert executor.submit(worker.process_next_job).result(timeout=30) is True

        with Session(engine) as db:
            resumed = db.get(BackgroundJob, jobs[1])
            assert resumed.status == 'EXITOSO' and resumed.active is False
            assert resumed.result['registros_traidos'] == resumed.result['registros_insertados'] == 5001
            assert resumed.result['checkpoint'] is None
            assert db.get(FuenteDatos, source_id).ultima_sync == datetime.fromisoformat(checkpoint['window_to'])
            assert db.query(RawSecop).filter_by(fuente_id=source_id).count() == 10001
            assert db.query(func.count(func.distinct(RawSecop.socrata_row_id))).filter_by(fuente_id=source_id).scalar() == 10001
            assert db.query(RawSecopHistorial).filter_by(fuente_id=source_id).count() == 0
            states = [state for (state,) in db.query(SincronizacionHistorial.estado).filter_by(fuente_id=source_id).order_by(SincronizacionHistorial.id)]
            assert states == [EstadoSync.ERROR, EstadoSync.EXITOSO]
        assert len(calls) == 9 and calls[7]['query'] == calls[1]['query']
        assert calls[8]['cursor'] == 'wire-09999'
        assert all(call['host'] == 'www.datos.gov.co' and call['query']['$order'] == ':id ASC' for call in calls)
        observations.update(total_rows=10001, committed_before_cut=5000, resumed_rows=5001,
                            failed_https_attempts=len(cuts), total_https_requests=len(calls),
                            resumed_cursor=calls[7]['cursor'], window_preserved=True,
                            duplicate_active_job=False, abandoned_recovery_while_live=0,
                            terminal_states=['ERROR','EXITOSO'], history_duplicates=0,
                            certificate_and_hostname_verified=True)
        print('NETWORK_CHECKPOINT_EVIDENCE=' + json.dumps(observations))
    finally:
        release_fault.set()
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
        server.shutdown(); server.server_close(); server_thread.join(timeout=5)
        with engine.begin() as db:
            if jobs:
                db.execute(delete(BackgroundJob).where(BackgroundJob.id.in_(jobs)))
            if source_id is not None:
                db.execute(delete(RawSecopHistorial).where(RawSecopHistorial.fuente_id == source_id))
                db.execute(delete(RawSecop).where(RawSecop.fuente_id == source_id))
                db.execute(delete(SincronizacionHistorial).where(SincronizacionHistorial.fuente_id == source_id))
                db.execute(delete(FuenteDatos).where(FuenteDatos.id == source_id))
            if admin_id is not None:
                db.execute(delete(AdminSession).where(AdminSession.admin_id == admin_id))
                db.execute(delete(Admin).where(Admin.id == admin_id))
        engine.dispose()
