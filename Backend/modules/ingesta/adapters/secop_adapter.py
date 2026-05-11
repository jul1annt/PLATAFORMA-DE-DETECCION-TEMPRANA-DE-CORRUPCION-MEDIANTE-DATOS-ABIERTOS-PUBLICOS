import requests
from datetime import datetime
from typing import Any
from .base_adapter import BaseProveedorAdapter

class SecopAdapter(BaseProveedorAdapter):

    FECHA_INICIAL  = "2020-01-01"
    BATCH_SIZE     = 5000   # registros por petición

    def __init__(self, endpoint: str, api_key: str = None):
        self.endpoint = endpoint
        self.api_key  = api_key

    def get_nombre(self) -> str:
        return "SECOP"

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
            "$limit":  params.get("$limit", self.BATCH_SIZE),
            "$offset": params.get("$offset", 0),
        }

        response = requests.get(
            self.endpoint,
            headers=headers,
            params=query_params,
            timeout=60
        )
        response.raise_for_status()
        return response.json()

    def fetch_todos(self, fecha_desde: str = None) -> Any:
        """
        Generador que pagina automáticamente hasta traer todos los registros.
        Uso: for batch in adapter.fetch_todos(): ...
        """
        fecha_desde = fecha_desde or self.FECHA_INICIAL
        fecha_hasta = datetime.today().strftime("%Y-%m-%d")

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-App-Token"] = self.api_key

        offset = 0
        while True:
            query_params = {
                "$where": (
                    f"fecha_de_publicacion_del BETWEEN "
                    f"'{fecha_desde}T00:00:00' AND '{fecha_hasta}T23:59:59'"
                ),
                "$limit":  self.BATCH_SIZE,
                "$offset": offset,
            }

            response = requests.get(
                self.endpoint,
                headers=headers,
                params=query_params,
                timeout=60
            )
            response.raise_for_status()
            batch = response.json()

            if not batch:
                break

            yield batch
            print(f"[SECOP] offset={offset} | batch={len(batch)}")

            if len(batch) < self.BATCH_SIZE:
                break  # último batch, ya no hay más

            offset += self.BATCH_SIZE