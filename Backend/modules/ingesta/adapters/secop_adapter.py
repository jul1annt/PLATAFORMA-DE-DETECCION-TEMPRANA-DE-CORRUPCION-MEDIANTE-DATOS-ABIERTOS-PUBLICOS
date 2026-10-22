import json
import time
from ipaddress import ip_address
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Generator
from urllib.parse import urlencode, urlparse

import requests
from urllib3 import HTTPSConnectionPool
from urllib3.exceptions import (
    ConnectTimeoutError,
    NewConnectionError,
    ProtocolError,
    ReadTimeoutError,
)
from urllib3.util import Timeout

from .base_adapter import BaseProveedorAdapter
from ..security import resolve_source_endpoint

class SecopAdapter(BaseProveedorAdapter):

    FECHA_INICIAL = "2020-01-01"
    # A 5,000-row response was measured at about 12.5 MB; the repository splits
    # it into PostgreSQL-safe insert statements before storing the checkpoint.
    BATCH_SIZE    = 5000

    REDIRECT_STATUSES = {301, 302, 303, 307, 308}
    RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}
    MAX_REQUEST_ATTEMPTS = 6
    MAX_RETRY_DELAY_SECONDS = 60

    @staticmethod
    def _soql_datetime(value: str) -> str:
        """Format an aware app timestamp as a UTC datetime literal for SoQL."""
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise requests.RequestException("La ventana SECOP contiene una fecha inválida") from exc
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed.replace(microsecond=0).isoformat()

    def __init__(
        self,
        endpoint: str,
        api_key: str = None,
        pinned_ips: tuple[str, ...] | None = None,
    ):
        if pinned_ips is None:
            endpoint, pinned_ips = resolve_source_endpoint(endpoint)
        parsed = urlparse(endpoint)
        if not parsed.hostname or not pinned_ips:
            raise requests.RequestException("El endpoint SECOP no tiene una dirección validada")
        for address in pinned_ips:
            if not ip_address(address).is_global:
                raise requests.RequestException("El endpoint SECOP contiene una dirección no pública")
        self.endpoint = endpoint
        self.api_key  = api_key
        self.host = parsed.hostname.lower().rstrip(".")
        self.path = parsed.path
        self.pinned_ips = tuple(dict.fromkeys(pinned_ips))
        self._pools: dict[str, HTTPSConnectionPool] = {}

    def close(self) -> None:
        for pool in self._pools.values():
            pool.close()
        self._pools.clear()

    def _pool_for(self, address: str) -> HTTPSConnectionPool:
        pool = self._pools.get(address)
        if pool is None:
            pool = HTTPSConnectionPool(
                host=address,
                port=443,
                assert_hostname=self.host,
                server_hostname=self.host,
                cert_reqs="CERT_REQUIRED",
                timeout=Timeout(connect=10, read=60),
                retries=False,
                maxsize=1,
                block=True,
            )
            self._pools[address] = pool
        return pool

    @classmethod
    def _retry_delay(cls, response, attempt: int) -> float:
        headers = getattr(response, "headers", None) or {}
        retry_after = headers.get("Retry-After")
        delay = None
        if retry_after:
            try:
                delay = float(retry_after)
            except (TypeError, ValueError):
                try:
                    retry_at = parsedate_to_datetime(str(retry_after))
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    delay = (retry_at - datetime.now(timezone.utc)).total_seconds()
                except (TypeError, ValueError, OverflowError):
                    delay = None
        if delay is None:
            delay = min(2 ** attempt, 30)
        return min(max(delay, 0), cls.MAX_RETRY_DELAY_SECONDS)

    def _request_json(self, headers: dict[str, str], params: dict) -> Any:
        last_connection_error = None
        for attempt in range(self.MAX_REQUEST_ATTEMPTS):
            address = self.pinned_ips[attempt % len(self.pinned_ips)]
            pool = self._pool_for(address)
            try:
                request_url = f"{self.path}?{urlencode(params)}"
                response = pool.urlopen(
                    "GET",
                    request_url,
                    headers={**headers, "Host": self.host},
                    timeout=Timeout(connect=10, read=60),
                    retries=False,
                    redirect=False,
                    assert_same_host=False,
                )
            except (
                ConnectTimeoutError,
                NewConnectionError,
                ProtocolError,
                ReadTimeoutError,
            ) as exc:
                last_connection_error = exc
                pool.close()
                self._pools.pop(address, None)
                continue

            response_released = False
            try:
                if response.status in self.REDIRECT_STATUSES:
                    raise requests.RequestException("La fuente intentó redirigir la solicitud")
                if response.status in self.RETRYABLE_STATUSES:
                    delay = self._retry_delay(response, attempt)
                    response.release_conn()
                    response_released = True
                    if attempt + 1 < self.MAX_REQUEST_ATTEMPTS:
                        time.sleep(delay)
                        continue
                if response.status >= 400:
                    raise requests.HTTPError(f"La fuente SECOP respondió HTTP {response.status}")
                try:
                    return json.loads(response.data)
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    raise requests.RequestException("La fuente SECOP devolvió JSON inválido") from exc
            finally:
                if not response_released:
                    response.release_conn()

        if last_connection_error is not None:
            raise requests.RequestException("No fue posible conectar con la fuente SECOP") from last_connection_error
        raise requests.RequestException("No hay direcciones públicas disponibles para la fuente SECOP")

    def get_nombre(self) -> str:
        return "SECOP"

    def _probe_ids(self, headers: dict[str, str], row_ids: list[str]) -> dict:
        if not row_ids:
            return {"sample_checked": 0, "sample_missing": 0}
        literals = ",".join("'" + value.replace("'", "''") + "'" for value in row_ids)
        matches = self._request_json(headers, {
            "$select": ":id",
            "$where": f":id in ({literals})",
            "$limit": len(row_ids),
            "$$exclude_system_fields": "false",
        })
        if not isinstance(matches, list):
            raise ValueError("SECOP no devolvió la muestra de identificadores")
        present = {str(item[":id"]) for item in matches}
        return {
            "sample_checked": len(row_ids),
            "sample_missing": sum(value not in present for value in row_ids),
        }

    def probe_ids(self, row_ids: list[str]) -> dict:
        """Cheap replacement check during a long, checkpointed full load."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-App-Token"] = self.api_key
        try:
            return self._probe_ids(headers, row_ids)
        except (KeyError, TypeError, ValueError) as exc:
            raise requests.RequestException("SECOP devolvió una muestra de IDs inválida") from exc
        finally:
            self.close()

    def probe_generation(self, row_ids: list[str]) -> dict:
        """Read source-wide signature and check local Socrata IDs outside the watermark."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-App-Token"] = self.api_key
        try:
            rows = self._request_json(headers, {
                "$select": "count(*) as filas,min(:updated_at) as min_actualizacion,"
                           "max(:updated_at) as max_actualizacion",
            })
            if not isinstance(rows, list) or len(rows) != 1:
                raise requests.RequestException("SECOP no devolvió una firma de generación válida")
            item = rows[0]
            signature = {
                "filas": int(item["filas"]),
                "min_actualizacion": item.get("min_actualizacion"),
                "max_actualizacion": item.get("max_actualizacion"),
            }
            if signature["filas"] < 0 or not signature["max_actualizacion"]:
                raise ValueError("Firma de generación incompleta")
            signature.update(self._probe_ids(headers, row_ids))
            return signature
        except (KeyError, TypeError, ValueError) as exc:
            raise requests.RequestException("SECOP devolvió una firma de generación inválida") from exc
        finally:
            self.close()

    def fetch(self, params: dict = {}) -> list[dict[str, Any]]:
        """Trae un batch específico (usado en probar_conexion)"""
        fecha_desde = params.get("fecha_desde", self.FECHA_INICIAL)
        fecha_hasta = datetime.today().strftime("%Y-%m-%d")

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-App-Token"] = self.api_key

        query_params = {
            "$where": (
                f"fecha_de_publicacion_del BETWEEN "
                f"'{fecha_desde}T00:00:00' AND '{fecha_hasta}T23:59:59'"
            ),
            "$limit":  params.get("$limit", 5),
            "$offset": params.get("$offset", 0),
        }

        try:
            return self._request_json(headers, query_params)
        finally:
            self.close()

    def fetch_todos(
        self,
        fecha_desde: str = None,
        fecha_hasta: str = None,
        fecha_actualizacion_desde: str | None = None,
        cursor_id: str | None = None,
    ) -> Generator:
        """
        Generador que pagina automáticamente.
        Uso: for batch in adapter.fetch_todos(): ...

        Se pagina en un orden total por el identificador interno de Socrata.
        Ordenar por fechas de publicación permitiría que una edición durante
        la descarga moviera una fila entre páginas basadas en offset.
        """
        fecha_desde = fecha_desde or f"{self.FECHA_INICIAL}T00:00:00"
        fecha_hasta = fecha_hasta or datetime.today().strftime("%Y-%m-%dT23:59:59")
        fecha_desde = self._soql_datetime(fecha_desde)
        fecha_hasta = self._soql_datetime(fecha_hasta)
        fecha_actualizacion_desde = self._soql_datetime(
            fecha_actualizacion_desde or fecha_desde
        )

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-App-Token"] = self.api_key

        try:
            while True:
                limit = self.BATCH_SIZE
                filtro_fecha = (
                    f"(fecha_de_ultima_publicaci BETWEEN '{fecha_desde}' AND '{fecha_hasta}' "
                    f"OR fecha_de_publicacion_del BETWEEN '{fecha_desde}' AND '{fecha_hasta}' "
                    f"OR (:updated_at > '{fecha_actualizacion_desde}' "
                    f"AND :updated_at <= '{fecha_hasta}'))"
                )
                if cursor_id is not None:
                    cursor_literal = cursor_id.replace("'", "''")
                    filtro_fecha = f"{filtro_fecha} AND :id > '{cursor_literal}'"

                query_params = {
                    "$where": filtro_fecha,
                    "$limit":  limit,
                    "$order": ":id ASC",
                    "$$exclude_system_fields": "false",
                }
                batch = self._request_json(headers, query_params)

                if not batch:
                    break

                try:
                    identifiers = [record[":id"] for record in batch]
                except (KeyError, TypeError, ValueError) as exc:
                    raise requests.RequestException(
                        "SECOP no devolvió identificadores internos para continuar la paginación"
                    ) from exc
                if any(
                    not isinstance(value, (str, int))
                    or isinstance(value, bool)
                    or not 1 <= len(str(value)) <= 256
                    or any(ord(character) < 32 for character in str(value))
                    for value in identifiers
                ):
                    raise requests.RequestException(
                        "SECOP devolvió un identificador interno inválido"
                    )
                identifiers = [str(value) for value in identifiers]
                if len(set(identifiers)) != len(identifiers):
                    raise requests.RequestException(
                        "SECOP devolvió identificadores internos duplicados"
                    )
                if cursor_id is not None and identifiers[0] == cursor_id:
                    raise requests.RequestException(
                        "SECOP no avanzó el cursor interno de paginación"
                    )

                yield batch
                cursor_id = identifiers[-1]

                if len(batch) < limit:
                    break
        finally:
            self.close()
