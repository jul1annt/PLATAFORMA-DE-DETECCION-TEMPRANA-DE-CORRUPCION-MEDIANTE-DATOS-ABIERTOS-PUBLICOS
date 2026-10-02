import socket
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from requests import HTTPError, RequestException
from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from urllib.parse import parse_qs, urlsplit
from urllib3.connection import connection as urllib3_socket_connection

from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.ingesta.model.SincronizacionHistorial import SincronizacionHistorial
from modules.ingesta.adapters.secop_adapter import SecopAdapter
from modules.ingesta.model.SincronizacionHistorial import EstadoSync
from modules.ingesta.dto.request import FuenteDatosUpdateDTO
from modules.ingesta.repository.IngestaRepository import IngestaRepository
from shared.enums import TipoFormato
from modules.ingesta.security import validate_source_endpoint


def _query_fields(url: str) -> dict[str, str]:
    return {key: values[-1] for key, values in parse_qs(urlsplit(url).query).items()}


def _rows_after_cursor(rows: list[dict], cursor: str | None) -> list[dict]:
    if cursor is None:
        return rows
    index = next(index for index, row in enumerate(rows) if row[":id"] == cursor)
    return rows[index + 1:]


@pytest.mark.parametrize("address", ["127.0.0.1", "10.1.2.3", "::1", "fd00::1", "fe80::1"])
def test_endpoint_blocks_private_ipv4_and_ipv6_destinations(monkeypatch, address):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (family, socket.SOCK_STREAM, 0, "", (address, 443))
    ])
    with pytest.raises(HTTPException) as private:
        validate_source_endpoint("https://www.datos.gov.co/resource/test.json")
    assert private.value.status_code == 422


def test_endpoint_allows_public_addresses_and_blocks_unresolved_host(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 443))
    ])
    assert validate_source_endpoint("https://www.datos.gov.co/resource/test.json")

    def unresolved(*_args, **_kwargs):
        raise socket.gaierror("temporary DNS failure")

    monkeypatch.setattr(socket, "getaddrinfo", unresolved)
    with pytest.raises(HTTPException) as failure:
        validate_source_endpoint("https://www.datos.gov.co/resource/test.json")
    assert failure.value.status_code == 422

    with pytest.raises(HTTPException) as foreign:
        validate_source_endpoint("https://example.net/resource/test.json")
    assert foreign.value.status_code == 422

    with pytest.raises(HTTPException) as non_resource:
        validate_source_endpoint("https://www.datos.gov.co/")
    assert non_resource.value.status_code == 422

    with pytest.raises(HTTPException) as custom_query:
        validate_source_endpoint("https://www.datos.gov.co/resource/test.json?next=https://example.net")
    assert custom_query.value.status_code == 422


def test_endpoint_rejects_empty_dns_results(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [])

    with pytest.raises(HTTPException) as failure:
        validate_source_endpoint("https://www.datos.gov.co/resource/test.json")

    assert failure.value.status_code == 422


def test_saved_source_is_revalidated_when_adapter_is_created(monkeypatch):
    source_url = "https://www.datos.gov.co/resource/test.json"
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 443))
    ])
    assert validate_source_endpoint(source_url)

    # A hostname that was public when configured can resolve differently on
    # a later synchronization; adapter creation must reject that new answer.
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 443))
    ])
    from modules.ingesta.adapters.adapter_factory import get_adapter

    with pytest.raises(HTTPException) as failure:
        get_adapter("SECOP", source_url)

    assert failure.value.status_code == 422


@pytest.mark.parametrize(
    ("resolved_ip", "family"),
    [("8.8.8.8", socket.AF_INET), ("2001:4860:4860::8888", socket.AF_INET6)],
)
def test_adapter_pins_validated_ip_for_socket_and_keeps_tls_host(monkeypatch, resolved_ip, family):
    from modules.ingesta.adapters.adapter_factory import get_adapter

    source_url = "https://www.datos.gov.co/resource/test.json"
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (family, socket.SOCK_STREAM, 0, "", (resolved_ip, 443))
    ])
    adapter = get_adapter("SECOP", source_url)

    # DNS changes after validation. The transport must keep using the public
    # address captured by the adapter while SNI/certificate/Host use SECOP.
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 443))
    ])
    captured = {}
    socket_target = {}

    def fake_connect(address, *_args, **_kwargs):
        socket_target["address"] = address
        return object()

    monkeypatch.setattr(urllib3_socket_connection, "create_connection", fake_connect)
    pool = adapter._pool_for(resolved_ip)
    connection = pool._new_conn()
    connection._new_conn()
    assert socket_target["address"] == (resolved_ip, 443)
    assert connection.server_hostname == "www.datos.gov.co"
    assert connection.assert_hostname == "www.datos.gov.co"

    class Response:
        status = 200
        data = b"[]"

        def release_conn(self):
            pass

    def fake_urlopen(pool, method, url, *, headers, **_kwargs):
        captured.update(
            pool_host=pool.host,
            hostname=pool.assert_hostname,
            server_hostname=pool.conn_kw["server_hostname"],
            request_host=headers["Host"],
            path=urlsplit(url).path,
            fields=_query_fields(url),
        )
        return Response()

    monkeypatch.setattr("modules.ingesta.adapters.secop_adapter.HTTPSConnectionPool.urlopen", fake_urlopen)
    assert adapter.fetch() == []
    assert captured == {
        "pool_host": resolved_ip,
        "hostname": "www.datos.gov.co",
        "server_hostname": "www.datos.gov.co",
        "request_host": "www.datos.gov.co",
        "path": "/resource/test.json",
        "fields": {
            "$where": "fecha_de_publicacion_del BETWEEN '2020-01-01T00:00:00' AND "
                      f"'{datetime.today().strftime('%Y-%m-%d')}T23:59:59'",
            "$limit": "5",
            "$offset": "0",
        },
    }


def test_secop_pagination_fetches_beyond_previous_ten_thousand_limit(monkeypatch):
    opaque_ids = {
        0: "row-zfip_ezaf_zmn9",
        1: "row-ffjc_ejtg.ekrs",
        2: "row-9idt_4bnd.4iwg",
        3: "row-g2sr.sk6h-kdfa",
        4: "row-9dew~avi2_wrqa",
        4999: "row-k2bs.uq2j~p359",
    }
    expected = [
        {
            ":id": opaque_ids.get(value, f"row-{value:05d}"),
            "id_del_proceso": str(value),
        }
        for value in range(10001)
    ]
    calls = []

    class Response:
        def __init__(self, batch):
            self.status = 200
            self.data = json.dumps(batch).encode()

        def release_conn(self):
            pass

    def fake_get(pool, method, url, *, headers, **kwargs):
        fields = _query_fields(url)
        assert method == "GET"
        assert pool.host == "8.8.8.8"
        assert pool.assert_hostname == "www.datos.gov.co"
        assert pool.conn_kw["server_hostname"] == "www.datos.gov.co"
        assert headers["Host"] == "www.datos.gov.co"
        assert kwargs["redirect"] is False
        assert kwargs["assert_same_host"] is False
        assert fields["$order"] == ":id ASC"
        assert fields["$$exclude_system_fields"] == "false"
        assert "$offset" not in fields
        cursor = (
            fields["$where"].rsplit(":id > '", 1)[1].split("'", 1)[0]
            if ":id > '" in fields["$where"]
            else None
        )
        calls.append(cursor)
        batch = _rows_after_cursor(expected, cursor)
        return Response(batch[:int(fields["$limit"])])

    monkeypatch.setattr("modules.ingesta.adapters.secop_adapter.HTTPSConnectionPool.urlopen", fake_get)
    adapter = SecopAdapter("https://www.datos.gov.co/resource/test.json", pinned_ips=("8.8.8.8",))
    fetched = [item for batch in adapter.fetch_todos() for item in batch]
    assert fetched == expected
    assert len(calls) == 3
    assert calls[0] is None
    assert calls[1] == opaque_ids[4999]
    assert calls[-1] == "row-09999"


def test_secop_retries_rate_limit_and_honors_retry_after(monkeypatch):
    from modules.ingesta.adapters.secop_adapter import SecopAdapter

    responses = iter([
        (429, {"Retry-After": "3"}, b'{"error":"rate limited"}'),
        (200, {}, b'[{":id":"row-1"}]'),
    ])
    calls = []
    delays = []

    class Response:
        def __init__(self, status, headers, data):
            self.status = status
            self.headers = headers
            self.data = data

        def release_conn(self):
            pass

    def fake_urlopen(_pool, *_args, **_kwargs):
        calls.append(True)
        return Response(*next(responses))

    monkeypatch.setattr("modules.ingesta.adapters.secop_adapter.HTTPSConnectionPool.urlopen", fake_urlopen)
    monkeypatch.setattr("modules.ingesta.adapters.secop_adapter.time.sleep", delays.append)
    adapter = SecopAdapter("https://www.datos.gov.co/resource/test.json", pinned_ips=("8.8.8.8",))

    try:
        assert adapter._request_json({}, {"$limit": 1}) == [{":id": "row-1"}]
    finally:
        adapter.close()

    assert len(calls) == 2
    assert delays == [3.0]


def test_secop_does_not_retry_non_transient_http_errors(monkeypatch):
    from modules.ingesta.adapters.secop_adapter import SecopAdapter

    calls = []

    class Response:
        status = 400
        headers = {}
        data = b'{"error":"bad request"}'

        def release_conn(self):
            pass

    def fake_urlopen(*_args, **_kwargs):
        calls.append(True)
        return Response()

    monkeypatch.setattr("modules.ingesta.adapters.secop_adapter.HTTPSConnectionPool.urlopen", fake_urlopen)
    adapter = SecopAdapter("https://www.datos.gov.co/resource/test.json", pinned_ips=("8.8.8.8",))

    try:
        with pytest.raises(HTTPError):
            adapter._request_json({}, {"$limit": 1})
    finally:
        adapter.close()

    assert len(calls) == 1


def test_secop_retries_transient_read_timeout(monkeypatch):
    from urllib3.exceptions import ReadTimeoutError

    calls = []

    class Response:
        status = 200
        headers = {}
        data = b'[]'

        def release_conn(self):
            pass

    def fake_urlopen(_pool, *_args, **_kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise ReadTimeoutError(None, "/resource/test.json", "timed out")
        return Response()

    monkeypatch.setattr("modules.ingesta.adapters.secop_adapter.HTTPSConnectionPool.urlopen", fake_urlopen)
    adapter = SecopAdapter("https://www.datos.gov.co/resource/test.json", pinned_ips=("8.8.8.8",))

    try:
        assert adapter._request_json({}, {"$limit": 1}) == []
    finally:
        adapter.close()

    assert len(calls) == 2


def test_secop_retries_transient_protocol_error(monkeypatch):
    from urllib3.exceptions import ProtocolError

    calls = []

    class Response:
        status = 200
        headers = {}
        data = b'[]'

        def release_conn(self):
            pass

    def fake_urlopen(_pool, *_args, **_kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise ProtocolError("remote end closed connection")
        return Response()

    monkeypatch.setattr(
        "modules.ingesta.adapters.secop_adapter.HTTPSConnectionPool.urlopen",
        fake_urlopen,
    )
    adapter = SecopAdapter("https://www.datos.gov.co/resource/test.json", pinned_ips=("8.8.8.8",))

    try:
        assert adapter._request_json({}, {"$limit": 1}) == []
    finally:
        adapter.close()

    assert len(calls) == 2


def test_secop_pagination_normalizes_timezone_offsets_for_soql(monkeypatch):
    captured = {}

    class Response:
        status = 200
        data = b"[]"

        def release_conn(self):
            pass

    def fake_urlopen(_pool, _method, url, **_kwargs):
        captured.update(_query_fields(url))
        return Response()

    monkeypatch.setattr("modules.ingesta.adapters.secop_adapter.HTTPSConnectionPool.urlopen", fake_urlopen)
    adapter = SecopAdapter(
        "https://www.datos.gov.co/resource/test.json",
        pinned_ips=("8.8.8.8",),
    )

    assert list(adapter.fetch_todos(
        fecha_desde="2026-09-01T00:00:00-05:00",
        fecha_hasta="2026-09-29T06:24:31.506245+00:00",
        fecha_actualizacion_desde="2026-09-20T12:00:00-05:00",
    )) == []

    assert captured["$where"] == (
        "(fecha_de_ultima_publicaci BETWEEN '2026-09-01T05:00:00' AND '2026-09-29T06:24:31' "
        "OR fecha_de_publicacion_del BETWEEN '2026-09-01T05:00:00' AND '2026-09-29T06:24:31' "
        "OR (:updated_at > '2026-09-20T17:00:00' AND :updated_at <= '2026-09-29T06:24:31'))"
    )


def test_secop_keyset_pagination_keeps_appended_rows_after_first_page(monkeypatch):
    rows = [
        {":id": f"row-{value:05d}", "id_del_proceso": str(value)}
        for value in range(5000)
    ]
    cursors = []

    class Response:
        def __init__(self, batch):
            self.status = 200
            self.data = json.dumps(batch).encode()

        def release_conn(self):
            pass

    def fake_get(_pool, method, url, **_kwargs):
        fields = _query_fields(url)
        assert method == "GET"
        assert fields["$order"] == ":id ASC"
        assert "$offset" not in fields
        cursor = (
            fields["$where"].rsplit(":id > '", 1)[1].split("'", 1)[0]
            if ":id > '" in fields["$where"]
            else None
        )
        cursors.append(cursor)
        batch = _rows_after_cursor(rows, cursor)
        result = batch[:int(fields["$limit"])]
        if cursor is None:
            # Socrata assigns later internal IDs to newly appended records;
            # keyset continuation finds them without shifting prior rows.
            rows.extend(
                {":id": f"row-{value:05d}", "id_del_proceso": str(value)}
                for value in range(5000, 5020)
            )
        return Response(result)

    monkeypatch.setattr("modules.ingesta.adapters.secop_adapter.HTTPSConnectionPool.urlopen", fake_get)
    adapter = SecopAdapter("https://www.datos.gov.co/resource/test.json", pinned_ips=("8.8.8.8",))

    fetched = [item for batch in adapter.fetch_todos() for item in batch]

    assert fetched == rows
    assert cursors == [None, "row-04999"]


def test_incremental_sync_replays_configured_overlap_window(monkeypatch):
    from modules.ingesta.services import IngestaService as service_module
    from modules.ingesta.services.IngestaService import IngestaService

    last_success = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
    captured = {}

    class Repository:
        def get_by_id(self, _source_id):
            return SimpleNamespace(
                id=7,
                nombre="SECOP",
                tipo="SECOP",
                endpoint="https://www.datos.gov.co/resource/test.json",
                api_key=None,
                ultima_sync=last_success,
            )

        def try_sync_lock(self, _source_id):
            return True

        def crear_historial(self, _source_id):
            return SimpleNamespace(id=11)

        def cerrar_historial(self, *_args, **_kwargs):
            pass

        def actualizar_ultima_sync(self, *_args, **_kwargs):
            pass

        def release_sync_lock(self, _source_id):
            pass

        def insertar_raw_secop_bulk(self, batch, _source_id):
            return len(batch)

    class Adapter:
        def fetch_todos(self, **kwargs):
            captured.update(kwargs)
            yield from ()

    monkeypatch.setattr(service_module.settings, "INGESTA_OVERLAP_HOURS", 48)
    monkeypatch.setattr(service_module, "get_adapter", lambda *_args: Adapter())
    service = IngestaService(db=None)
    service.repo = Repository()

    service.sincronizar_fuente(7)

    assert datetime.fromisoformat(captured["fecha_desde"]) == last_success - timedelta(hours=48)
    assert datetime.fromisoformat(captured["fecha_actualizacion_desde"]) == last_success
    assert datetime.fromisoformat(captured["fecha_hasta"]) >= last_success


def test_capped_sync_persists_cursor_and_next_job_resumes_same_window(monkeypatch):
    from modules.ingesta.services import IngestaService as service_module
    from modules.ingesta.services.IngestaService import IngestaService

    last_success = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
    checkpoint = None
    finished = []
    saved_batches = []
    adapter_calls = []

    class Repository:
        def get_by_id(self, _source_id):
            return SimpleNamespace(
                id=7,
                nombre="SECOP",
                tipo="SECOP",
                endpoint="https://www.datos.gov.co/resource/test.json",
                api_key=None,
                ultima_sync=last_success,
            )

        def try_sync_lock(self, _source_id):
            return True

        def crear_historial(self, _source_id):
            return SimpleNamespace(id=len(finished) + 1)

        def get_sync_checkpoint(self, _source_id, _job_id):
            return dict(checkpoint) if checkpoint else None

        def guardar_sync_checkpoint(self, _source_id, _job_id, next_checkpoint):
            nonlocal checkpoint
            checkpoint = dict(next_checkpoint)

        def persistir_lote_y_checkpoint(self, rows, _source_id, _job_id, next_checkpoint):
            nonlocal checkpoint
            checkpoint = dict(next_checkpoint)
            saved_batches.append([row["id_del_proceso"] for row in rows])
            return len(rows)

        def insertar_raw_secop_bulk(self, rows, _source_id):
            return len(rows)

        def actualizar_ultima_sync(self, _source_id, timestamp, job_id=None):
            nonlocal checkpoint
            checkpoint = None
            finished.append(("watermark", timestamp, job_id))

        def cerrar_historial(self, _id, _rows, _inserted, state, error=None):
            finished.append(("history", state, error))

        def release_sync_lock(self, _source_id):
            pass

    class Adapter:
        def __init__(self, batches):
            self.batches = batches

        def fetch_todos(self, **kwargs):
            adapter_calls.append(kwargs)
            yield from self.batches

    source_batches = [
        [
            {":id": "row-a", "id_del_proceso": "A"},
            {":id": "row-b", "id_del_proceso": "B"},
        ],
        [
            {":id": "row-c", "id_del_proceso": "C"},
            {":id": "row-d", "id_del_proceso": "D"},
        ],
        [
            {":id": "row-e", "id_del_proceso": "E"},
        ],
    ]
    adapters = [Adapter(source_batches[:2]), Adapter(source_batches[2:])]
    monkeypatch.setattr(service_module.settings, "INGESTA_MAX_RECORDS_PER_SYNC", 3)
    monkeypatch.setattr(service_module, "get_adapter", lambda *_args: adapters.pop(0))
    service = IngestaService(db=None)
    service.repo = Repository()

    partial = service.sincronizar_fuente(7, job_id=100)
    resumed = service.sincronizar_fuente(7, job_id=101)

    assert partial["parcial"] is True
    assert partial["cursor"] == "row-c"
    assert saved_batches == [["A", "B"], ["C"], ["E"]]
    assert adapter_calls[0]["cursor_id"] is None
    assert adapter_calls[1]["cursor_id"] == "row-c"
    assert adapter_calls[1]["fecha_hasta"] == adapter_calls[0]["fecha_hasta"]
    assert resumed["parcial"] is False
    assert resumed["registros_traidos"] == 1
    assert any(
        event[0] == "history"
        and event[1] == EstadoSync.PARCIAL
        and "límite" in event[2]
        for event in finished
    )
    assert any(event[0] == "watermark" for event in finished)


def test_secop_does_not_follow_redirects_with_source_credentials(monkeypatch):
    captured = {}

    class RedirectResponse:
        status = 302
        data = b""

        def release_conn(self):
            pass

    def fake_get(pool, method, url, **kwargs):
        captured.update(
            url=url,
            method=method,
            host=pool.host,
            assert_hostname=pool.assert_hostname,
            server_hostname=pool.conn_kw["server_hostname"],
            **kwargs,
        )
        return RedirectResponse()

    monkeypatch.setattr("modules.ingesta.adapters.secop_adapter.HTTPSConnectionPool.urlopen", fake_get)
    adapter = SecopAdapter(
        "https://www.datos.gov.co/resource/test.json",
        api_key="source-secret",
        pinned_ips=("8.8.8.8",),
    )

    with pytest.raises(RequestException, match="intentó redirigir"):
        adapter.fetch()

    assert captured["host"] == "8.8.8.8"
    assert captured["assert_hostname"] == "www.datos.gov.co"
    assert captured["server_hostname"] == "www.datos.gov.co"
    assert captured["headers"]["Host"] == "www.datos.gov.co"
    assert captured["redirect"] is False
    assert captured["headers"]["X-App-Token"] == "source-secret"


@pytest.mark.parametrize(
    ("payload", "expected_key", "expected_key_in_update"),
    [
        ({"endpoint": "https://datos.gov.co/resource/next.json"}, None, True),
        ({"endpoint": "https://datos.gov.co/resource/next.json", "api_key": None}, None, True),
        ({"endpoint": "https://datos.gov.co/resource/next.json", "api_key": "replacement"}, "stored:replacement", True),
        ({"api_key": None}, None, True),
        ({"frecuencia_dias": 30}, "old-encrypted-key", False),
    ],
)
def test_updating_source_never_carries_credentials_to_another_origin(
    monkeypatch, payload, expected_key, expected_key_in_update
):
    from modules.ingesta.services import IngestaService as service_module
    from modules.ingesta.services.IngestaService import IngestaService

    fuente = SimpleNamespace(
        id=7,
        nombre="SECOP",
        tipo="SECOP",
        formato=TipoFormato.JSON,
        endpoint="https://www.datos.gov.co/resource/current.json",
        api_key="old-encrypted-key",
        frecuencia_dias=15,
        activo=True,
        ultima_sync=None,
        created_at=datetime.now(timezone.utc),
    )

    class Repository:
        update_data = None

        def get_by_id(self, _source_id):
            return fuente

        def update(self, current, data):
            self.update_data = data
            for name, value in data.items():
                setattr(current, name, value)
            return current

    repository = Repository()
    service = IngestaService(db=None)
    service.repo = repository
    monkeypatch.setattr(service_module, "validate_source_endpoint", lambda value: str(value))
    monkeypatch.setattr(
        service_module,
        "encrypt_api_key",
        lambda value: f"stored:{value}" if value else None,
    )

    service.actualizar_fuente(7, FuenteDatosUpdateDTO(**payload))

    assert fuente.api_key == expected_key
    assert ("api_key" in repository.update_data) is expected_key_in_update


def test_failed_sync_records_partial_counts_and_keeps_success_cursor(monkeypatch, caplog):
    from modules.ingesta.services import IngestaService as service_module
    from shared.errors import IngestaError
    secret_detail = "database-password=must-not-leak"

    class Adapter:
        def fetch_todos(self, **_kwargs):
            yield [{"id_del_proceso": "1"}, {"id_del_proceso": "2"}]
            raise RuntimeError(secret_detail)

    class Repository:
        def __init__(self):
            self.cierre = None
            self.actualizaciones = []
            self.liberado = False

        def get_by_id(self, _fuente_id):
            return SimpleNamespace(
                id=7,
                nombre="SECOP",
                tipo="SECOP",
                endpoint="https://www.datos.gov.co/resource/test.json",
                api_key=None,
                ultima_sync=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

        def try_sync_lock(self, _fuente_id):
            return True

        def crear_historial(self, _fuente_id):
            return SimpleNamespace(id=11)

        def insertar_raw_secop_bulk(self, batch, _fuente_id):
            return len(batch)

        def cerrar_historial(self, historial_id, traidos, insertados, estado, error=None):
            self.cierre = (historial_id, traidos, insertados, estado, error)

        def actualizar_ultima_sync(self, fuente_id, watermark):
            self.actualizaciones.append((fuente_id, watermark))

        def release_sync_lock(self, _fuente_id):
            self.liberado = True

    from modules.ingesta.services.IngestaService import IngestaService

    repository = Repository()
    service = IngestaService(db=None)
    service.repo = repository
    monkeypatch.setattr(service_module, "get_adapter", lambda *_args: Adapter())
    caplog.set_level("ERROR")

    with pytest.raises(IngestaError) as failure:
        service.sincronizar_fuente(7)

    assert failure.value.code == "sync_failed"
    assert repository.cierre[:4] == (11, 2, 2, EstadoSync.ERROR)
    assert repository.cierre[4].startswith("Error interno ")
    assert secret_detail not in failure.value.detail
    assert secret_detail not in caplog.text
    assert repository.cierre[4].split()[-1] in caplog.text
    assert repository.actualizaciones == []
    assert repository.liberado


def test_sync_history_summary_aggregates_all_states_in_database():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    FuenteDatos.__table__.create(engine)
    SincronizacionHistorial.__table__.create(engine)

    with Session(engine) as db:
        fuente = FuenteDatos(
            nombre="SECOP test",
            tipo="SECOP",
            formato=TipoFormato.JSON,
            endpoint="https://www.datos.gov.co/resource/test.json",
        )
        segunda_fuente = FuenteDatos(
            nombre="SISCON test",
            tipo="SECOP",
            formato=TipoFormato.JSON,
            endpoint="https://www.datos.gov.co/resource/test2.json",
        )
        db.add(fuente)
        db.add(segunda_fuente)
        db.flush()
        db.add_all([
            SincronizacionHistorial(fuente_id=fuente.id, estado=EstadoSync.EXITOSO),
            SincronizacionHistorial(fuente_id=fuente.id, estado=EstadoSync.EXITOSO),
            SincronizacionHistorial(fuente_id=fuente.id, estado=EstadoSync.EN_PROCESO),
            SincronizacionHistorial(
                fuente_id=fuente.id,
                estado=EstadoSync.ERROR,
                mensaje_error="test failure",
            ),
            SincronizacionHistorial(fuente_id=segunda_fuente.id, estado=EstadoSync.EXITOSO),
        ])
        db.flush()

        repository = IngestaRepository(db)
        assert repository.resumen_historial() == {
            "total": 5,
            "exitoso": 3,
            "en_proceso": 1,
            "error": 1,
            "parcial": 0,
        }
        assert [row.id for row in repository.get_historial(limit=2, skip=1)] == [4, 3]
        page_rows, total = repository.get_historial_pagina(skip=1, limit=2, fuente_id=fuente.id)
        assert total == 4
        assert [(row.id, source_name) for row, source_name in page_rows] == [
            (3, "SECOP test"),
            (2, "SECOP test"),
        ]
        comparativa = repository.get_comparativa_fuentes()
        assert comparativa[0]["ultima_sync_estado"] == EstadoSync.ERROR
        assert comparativa[0]["ultima_sync_error"] == "test failure"

    engine.dispose()
