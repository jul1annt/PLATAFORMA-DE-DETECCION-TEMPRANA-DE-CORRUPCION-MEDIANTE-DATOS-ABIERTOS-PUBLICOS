from .base_adapter import BaseProveedorAdapter
from .secop_adapter import SecopAdapter
from modules.ingesta.security import decrypt_api_key, resolve_source_endpoint

ADAPTADORES_DISPONIBLES: dict[str, type[BaseProveedorAdapter]] = {
    "SECOP": SecopAdapter,
}

def get_adapter(tipo: str, endpoint: str, api_key: str = None) -> BaseProveedorAdapter:
    adapter_cls = ADAPTADORES_DISPONIBLES.get(tipo.upper())

    if not adapter_cls:
        raise ValueError(f"Proveedor '{tipo}' no registrado.")

    endpoint, pinned_ips = resolve_source_endpoint(endpoint)
    return adapter_cls(
        endpoint=endpoint,
        api_key=decrypt_api_key(api_key),
        pinned_ips=pinned_ips,
    )
