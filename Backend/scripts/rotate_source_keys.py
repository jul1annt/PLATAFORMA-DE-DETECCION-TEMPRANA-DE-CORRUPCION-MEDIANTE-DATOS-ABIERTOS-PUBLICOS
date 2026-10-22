"""Rotate encrypted source credentials to ENCRYPTION_KEY.

Run from Backend with ENCRYPTION_KEY set to the new key and
ENCRYPTION_KEY_OLD set to the key currently encrypting stored values:

    python scripts/rotate_source_keys.py
    python scripts/rotate_source_keys.py --apply

The application should also have ENCRYPTION_KEY_PREVIOUS set to the old key
while the data is being migrated, so API and worker processes can read both
old and new ciphertexts during a rolling deployment.
"""

import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import settings
from core.database import SessionLocal
from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.ingesta.security import ENCRYPTED_PREFIX, rotate_api_key


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-encrypt source API keys")
    parser.add_argument("--apply", action="store_true", help="Persist rotated values")
    args = parser.parse_args()

    old_key = os.getenv("ENCRYPTION_KEY_OLD")
    if not old_key:
        parser.error("Defina ENCRYPTION_KEY_OLD en el entorno; no se muestra ni registra su valor")
    if old_key == settings.ENCRYPTION_KEY:
        parser.error("ENCRYPTION_KEY_OLD debe ser distinta de la ENCRYPTION_KEY activa")

    db = SessionLocal()
    try:
        sources = db.query(FuenteDatos).filter(FuenteDatos.api_key.is_not(None)).all()
        candidates = [source for source in sources if source.api_key]

        # Calculate all replacements before mutating ORM objects. A wrong key or
        # malformed ciphertext therefore cannot leave a partially changed unit
        # of work, even before the database transaction is rolled back.
        replacements = [(source, rotate_api_key(source.api_key, old_key)) for source in candidates]
        changed = [(source, value) for source, value in replacements if value != source.api_key]
        legacy = sum(not source.api_key.startswith(ENCRYPTED_PREFIX) for source in candidates)
        print(f"Credenciales candidatas: {len(candidates)}")
        print(f"Cifradas con clave anterior: {len(changed) - legacy}")
        print(f"Legadas en texto claro: {legacy}")
        print(f"Ya compatibles con clave activa: {len(candidates) - len(changed)}")

        if not args.apply:
            print("Diagnóstico sin escritura. Verifique respaldo y despliegue antes de usar --apply.")
            return

        for source, value in changed:
            source.api_key = value
        db.commit()
        print(f"Credenciales actualizadas: {len(changed)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
