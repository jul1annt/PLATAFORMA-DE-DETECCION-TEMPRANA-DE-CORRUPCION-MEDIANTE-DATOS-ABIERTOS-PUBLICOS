"""Generate or verify the API access matrix from FastAPI's OpenAPI contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
OUTPUT_PATH = REPOSITORY_ROOT / "docs" / "seguridad" / "MATRIZ_ACCESO_API.md"
sys.path.insert(0, str(BACKEND_ROOT))

from main import app  # noqa: E402


METHODS = {"get", "post", "put", "patch", "delete"}
PUBLIC_OPERATIONS = {
    ("POST", "/api/auth/login"),
    ("POST", "/api/procesados/export/{formato}/jobs"),
}
ADMIN_PATH_PREFIXES = (
    "/api/analitica",
    "/api/ingesta/fuentes",
    "/api/jobs",
    "/api/procesados/logs",
)


def _has_bearer_security(operation: dict) -> bool:
    return any("HTTPBearer" in requirement for requirement in operation.get("security", []))


def validate_policy(spec: dict) -> None:
    for path, operations in spec.get("paths", {}).items():
        for method, operation in operations.items():
            method = method.upper()
            if method.lower() not in METHODS:
                continue
            bearer = _has_bearer_security(operation)
            if any(path.startswith(prefix) for prefix in ADMIN_PATH_PREFIXES) and not bearer:
                raise ValueError(f"La ruta administrativa {method} {path} no exige bearer")
            if method != "GET" and (method, path) not in PUBLIC_OPERATIONS and not bearer:
                raise ValueError(f"La mutación {method} {path} no tiene política de acceso")
            if path.startswith("/api/analitica") and not bearer:
                raise ValueError(f"El análisis {method} {path} no está reservado a administradores")


def _access_label(method: str, path: str, operation: dict) -> str:
    if path.startswith("/api/exports/"):
        return "Capacidad HMAC en `X-Export-Token` (por trabajo y vencimiento)"
    if _has_bearer_security(operation):
        return "Administrador autenticado (Bearer; cuenta activa)"
    if (method, path) == ("POST", "/api/auth/login"):
        return "Público: inicio de sesión"
    if (method, path) == ("POST", "/api/procesados/export/{formato}/jobs"):
        return "Público: crea exportación acotada; descarga exige capacidad"
    return "Público: lectura"


def render_matrix(spec: dict) -> str:
    validate_policy(spec)
    rows = []
    for path, operations in spec.get("paths", {}).items():
        for method, operation in operations.items():
            if method.lower() not in METHODS:
                continue
            summary = str(operation.get("summary", "")).replace("|", "\\|").replace("\n", " ")
            upper_method = method.upper()
            rows.append((path, upper_method, _access_label(upper_method, path, operation), summary))
    rows.sort(key=lambda row: (row[0], row[1]))

    lines = [
        "# Matriz de acceso de la API",
        "",
        "Fuente: `Backend/openapi.json`, generado por FastAPI. Se actualiza y verifica con `python scripts/export_access_matrix.py`.",
        "",
        "## Política",
        "",
        "- Las rutas de lectura de contratos SECOP, métricas públicas y autocompletado son públicas; las escrituras y reprocesamientos administrativos requieren un bearer de una cuenta administradora activa.",
        "- Toda la superficie `/api/analitica` es administrativa porque publica hallazgos, clasificaciones y ejecuciones sobre proveedores o contratos.",
        "- La gestión de fuentes, historiales de sincronización, logs de procesamiento y trabajos internos requiere administrador. Las claves de fuente no se publican.",
        "- El login es público. El registro requiere administrador; no existe alta anónima.",
        "- La creación de exportación de datos públicos no requiere sesión, pero se limita por volumen. Estado y descarga requieren `X-Export-Token`, firmado para un trabajo y su vencimiento; el token no va en la URL.",
        "- Las rutas rechazan parámetros de consulta desconocidos donde se valida una consulta; los formatos, rangos y límites se validan en el servidor.",
        "",
        "## Rutas",
        "",
        "| Método | Ruta | Acceso | Operación |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| {method} | `{path}` | {access} | {summary} |"
        for path, method, access, summary in rows
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="falla si la matriz guardada está desactualizada")
    args = parser.parse_args()
    generated = render_matrix(app.openapi())
    if args.check:
        if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_text(encoding="utf-8") != generated:
            print("La matriz de acceso está desactualizada; ejecuta python scripts/export_access_matrix.py", file=sys.stderr)
            return 1
        print("La matriz de acceso coincide con el contrato OpenAPI")
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(generated, encoding="utf-8", newline="\n")
    print(f"Matriz de acceso actualizada: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
