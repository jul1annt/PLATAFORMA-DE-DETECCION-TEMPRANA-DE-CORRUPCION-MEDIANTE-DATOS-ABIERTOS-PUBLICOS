"""Read-only SECOP generation check against a guarded local database."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    allowed = {
        ("plataforma_secop_refresh_test", 5433),
        ("plataformaanticorrupcion", 5432),
    }
    if (args.database, args.port) not in allowed:
        raise SystemExit("The database and port do not match an allowed local source")
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    os.environ.update(DB_HOST="127.0.0.1", DB_PORT=str(args.port), DB_NAME=args.database)
    sys.path.insert(0, str(root))

    from sqlalchemy import text
    from core.database import SessionLocal
    from modules.ingesta.repository.IngestaRepository import IngestaRepository
    from modules.ingesta.adapters.adapter_factory import get_adapter

    with SessionLocal() as db:
        identity = db.execute(text("SELECT current_database(), inet_server_addr()::text")).one()
        if identity[0] != args.database or not identity[1].startswith("127.0.0.1"):
            raise RuntimeError("Database identity guard failed")
        repo = IngestaRepository(db)
        source = repo.get_by_id(1)
        if not source or source.tipo != "SECOP" or not source.endpoint.endswith("/p6dx-8zbt.json"):
            raise RuntimeError("SECOP source identity guard failed")
        has_rows, sample = repo.local_generation_sample(source.id)
        probe = get_adapter(source.tipo, source.endpoint, source.api_key).probe_generation(sample)
        replaced = probe["sample_checked"] >= 5 and probe["sample_missing"] / probe["sample_checked"] >= 0.8
        print(json.dumps({
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "database": args.database,
            "has_local_rows": has_rows,
            "local_sample_count": len(sample),
            "source": probe,
            "replacement_detected": replaced,
            "identity_unverifiable": has_rows and len(sample) < 5,
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
