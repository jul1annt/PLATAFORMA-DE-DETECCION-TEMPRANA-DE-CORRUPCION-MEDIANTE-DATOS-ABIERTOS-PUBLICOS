"""Encrypt legacy plaintext source keys after a database backup.

Run from Backend: python scripts/migrate_source_keys.py
Then:             python scripts/migrate_source_keys.py --apply
"""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.database import SessionLocal
from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.ingesta.security import ENCRYPTED_PREFIX, encrypt_api_key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write encrypted values")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        sources = db.query(FuenteDatos).filter(FuenteDatos.api_key.is_not(None)).all()
        legacy = [source for source in sources if source.api_key and not source.api_key.startswith(ENCRYPTED_PREFIX)]
        print(f"Legacy plaintext keys: {len(legacy)}")
        if not args.apply:
            print("Dry run. Use --apply after confirming the backup and ENCRYPTION_KEY.")
            return
        for source in legacy:
            source.api_key = encrypt_api_key(source.api_key)
        db.commit()
        print(f"Encrypted keys: {len(legacy)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
