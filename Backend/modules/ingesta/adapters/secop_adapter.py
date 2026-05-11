import requests
from datetime import datetime
from typing import Any
from .base_adapter import BaseProveedorAdapter

class SecopAdapter(BaseProveedorAdapter):

    FECHA_INICIAL = "2020-01-01"

    def __init__(self, endpoint: str, api_key: str = None):
        self.endpoint = endpoint
        self.api_key = api_key

    def get_nombre(self) -> str:
        return "SECOP"

    def fetch(self, params: dict = {}) -> list[dict[str, Any]]:
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
            "$limit": params.get("$limit", 1000),
        }

        response = requests.get(
            self.endpoint,
            headers=headers,
            params=query_params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()