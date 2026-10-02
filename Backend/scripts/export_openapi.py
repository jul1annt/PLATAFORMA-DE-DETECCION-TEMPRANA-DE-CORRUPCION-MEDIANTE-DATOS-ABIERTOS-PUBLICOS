"""Generate or verify the checked-in OpenAPI contract without opening a DB connection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = BACKEND_ROOT / "openapi.json"
sys.path.insert(0, str(BACKEND_ROOT))

from main import app  # noqa: E402


def render_openapi() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if openapi.json differs from the application schema",
    )
    args = parser.parse_args()
    generated = render_openapi()

    if args.check:
        if not OPENAPI_PATH.is_file() or OPENAPI_PATH.read_text(encoding="utf-8") != generated:
            print("openapi.json está desactualizado; ejecuta python scripts/export_openapi.py", file=sys.stderr)
            return 1
        print("openapi.json coincide con el contrato de la aplicación")
        return 0

    OPENAPI_PATH.write_text(generated, encoding="utf-8", newline="\n")
    print(f"Contrato OpenAPI actualizado: {OPENAPI_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
