from abc import ABC, abstractmethod
from typing import Any

class BaseProveedorAdapter(ABC):

    @abstractmethod
    def fetch(self, params: dict = {}) -> list[dict[str, Any]]:
        """Trae los datos crudos del proveedor"""
        pass

    @abstractmethod
    def get_nombre(self) -> str:
        """Retorna el identificador del proveedor"""
        pass