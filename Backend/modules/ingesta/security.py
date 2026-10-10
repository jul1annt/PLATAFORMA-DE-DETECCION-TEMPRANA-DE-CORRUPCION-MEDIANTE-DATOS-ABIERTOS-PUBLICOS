import ipaddress
import re
import socket
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from core.config import settings

ENCRYPTED_PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    try:
        return Fernet(settings.ENCRYPTION_KEY.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("ENCRYPTION_KEY no es una clave Fernet válida") from exc


def encrypt_api_key(value: str | None) -> str | None:
    if not value:
        return value
    token = _fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{ENCRYPTED_PREFIX}{token}"


def decrypt_api_key(value: str | None) -> str | None:
    if not value:
        return None
    if not value.startswith(ENCRYPTED_PREFIX):
        # Compatibilidad temporal para permitir migrar registros existentes.
        return value
    token = value[len(ENCRYPTED_PREFIX):].encode("utf-8")
    try:
        return _fernet().decrypt(token).decode("utf-8")
    except InvalidToken as current_error:
        previous_key = settings.ENCRYPTION_KEY_PREVIOUS
        if previous_key:
            try:
                return Fernet(previous_key.encode("utf-8")).decrypt(token).decode("utf-8")
            except InvalidToken:
                pass
            except (TypeError, ValueError) as exc:
                raise RuntimeError("ENCRYPTION_KEY_PREVIOUS no es una clave Fernet válida") from exc
        raise RuntimeError("No fue posible descifrar la credencial de la fuente") from current_error


def rotate_api_key(value: str | None, previous_key: str) -> str | None:
    """Re-encrypt one stored value with the active key, without logging its content."""
    if not value:
        return value
    if not value.startswith(ENCRYPTED_PREFIX):
        return encrypt_api_key(value)

    try:
        previous_fernet = Fernet(previous_key.encode("utf-8"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise RuntimeError("La clave anterior de cifrado no es válida") from exc

    try:
        plaintext = previous_fernet.decrypt(value[len(ENCRYPTED_PREFIX):].encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Allow dry-run/apply to resume after partial rotation. Values already
        # readable by the active key are left unchanged.
        decrypt_api_key(value)
        return value
    return encrypt_api_key(plaintext)


def endpoint_origin(value: str) -> tuple[str, str, int]:
    parsed = urlparse(value)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), port


def resolve_source_endpoint(value: str) -> tuple[str, tuple[str, ...]]:
    parsed = urlparse(str(value))
    host = (parsed.hostname or "").lower().rstrip(".")
    allowed = {item.lower().rstrip(".") for item in settings.INGESTA_ALLOWED_HOSTS}
    if parsed.scheme.lower() != "https" or not host or host not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El endpoint debe usar HTTPS y pertenecer a un proveedor autorizado",
        )
    if not re.fullmatch(r"/resource/[a-z0-9-]+\.json", parsed.path, flags=re.IGNORECASE):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El endpoint debe apuntar a un recurso SECOP autorizado",
        )
    if parsed.query or parsed.fragment:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El endpoint no puede incluir parámetros ni fragmentos",
        )
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El endpoint contiene credenciales o un puerto no autorizado",
        )
    try:
        addresses = tuple(dict.fromkeys(
            item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        ))
    except socket.gaierror as exc:
        raise HTTPException(status_code=422, detail="No fue posible resolver el endpoint") from exc
    if not addresses:
        raise HTTPException(status_code=422, detail="El endpoint no resolvió direcciones")
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="El endpoint resolvió una dirección inválida") from exc
        if not ip.is_global:
            raise HTTPException(status_code=422, detail="El endpoint resuelve a una red no autorizada")
    return str(value), tuple(addresses)


def validate_source_endpoint(value: str) -> str:
    endpoint, _ = resolve_source_endpoint(value)
    return endpoint
