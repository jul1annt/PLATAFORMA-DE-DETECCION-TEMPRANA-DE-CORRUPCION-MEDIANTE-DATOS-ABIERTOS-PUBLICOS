from .base_adapter import BaseProveedorAdapter
from .secop_adapter import SecopAdapter

ADAPTADORES_DISPONIBLES: dict[str, type[BaseProveedorAdapter]] = {
    "SECOP_II": SecopAdapter,
    # "OTRO_PROVEEDOR": OtroProveedorAdapter,  <-- así se registra el próximo
}

def get_adapter(nombre_proveedor: str, api_key: str) -> BaseProveedorAdapter:
    adapter_cls = ADAPTADORES_DISPONIBLES.get(nombre_proveedor.upper())

    if not adapter_cls:
        raise ValueError(f"Proveedor '{nombre_proveedor}' no registrado.")

    # pyrefly: ignore [unexpected-keyword]
    return adapter_cls(api_key=api_key)