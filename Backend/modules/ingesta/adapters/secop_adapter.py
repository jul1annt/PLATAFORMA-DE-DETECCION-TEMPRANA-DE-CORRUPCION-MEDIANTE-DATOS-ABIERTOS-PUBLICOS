import requests
from typing import Any
from .base_adapter import BaseProveedorAdapter

class SecopAdapter(BaseProveedorAdapter):

    BASE_URL = "https://www.datos.gov.co/resource/p6dx-8zbt.json"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-App-Token": self.api_key,
            "Accept": "application/json"
        }

    def get_nombre(self) -> str:
        return "SECOP_II"

    def fetch(self, params: dict = {}) -> list[dict[str, Any]]:
        default_params = {"$limit": 1000}
        default_params.update(params)

        response = requests.get(
            self.BASE_URL,
            headers=self.headers,
            params=default_params
        )
        response.raise_for_status()
        return response.json()