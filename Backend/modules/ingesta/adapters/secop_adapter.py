import requests
from typing import Any
from .base_adapter import BaseProveedorAdapter

class SecopAdapter(BaseProveedorAdapter):

    def __init__(self, endpoint: str, api_key: str = None):
        self.endpoint = endpoint
        self.headers = {"Accept": "application/json"}
        if api_key:
            self.headers["X-App-Token"] = api_key

    def get_nombre(self) -> str:
        return "SECOP"

    def fetch(self, params: dict = {}) -> list[dict[str, Any]]:
        default_params = {"$limit": 1000}
        default_params.update(params)

        response = requests.get(
            self.endpoint,
            headers=self.headers,
            params=default_params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()