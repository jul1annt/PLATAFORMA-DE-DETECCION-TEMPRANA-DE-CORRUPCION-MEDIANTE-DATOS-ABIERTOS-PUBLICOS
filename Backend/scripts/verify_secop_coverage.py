"""Compare a completed isolated SECOP load with the same official source generation."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"plataforma_secop_refresh_test", "plataforma_secop_refresh_20261001_test"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, choices=sorted(ALLOWED))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    os.environ.update(DB_HOST="127.0.0.1", DB_PORT="5433", DB_NAME=args.database)
    sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from core.database import SessionLocal
    from modules.ingesta.repository.IngestaRepository import IngestaRepository
    from modules.ingesta.adapters.adapter_factory import get_adapter

    with SessionLocal() as db:
        identity = db.execute(text("SELECT current_database(), current_setting('data_directory')")).one()
        if identity[0] != args.database or "recovery-clone-20260929" not in identity[1]:
            raise RuntimeError("Isolated database guard failed")
        repo = IngestaRepository(db)
        source = repo.get_by_id(1)
        if not source or source.tipo != "SECOP" or not source.endpoint.endswith("/p6dx-8zbt.json"):
            raise RuntimeError("SECOP source guard failed")
        adapter = get_adapter(source.tipo, source.endpoint, source.api_key)
        _, sample = repo.local_generation_sample(source.id)
        before = adapter.probe_generation(sample)
        if before["sample_checked"] < 5 or before["sample_missing"]:
            raise RuntimeError(f"Local IDs do not match the official generation: {before}")

        local_total = db.execute(text("SELECT count(*) FROM raw_secop WHERE fuente_id=1")).scalar_one()
        local_missing_ids = db.execute(text(
            "SELECT count(*) FROM raw_secop WHERE fuente_id=1 AND socrata_row_id IS NULL"
        )).scalar_one()
        local_years = dict(db.execute(text("""
            SELECT COALESCE(EXTRACT(YEAR FROM fecha_de_publicacion_del)::text, 'SIN_FECHA'), count(*)
            FROM raw_secop WHERE fuente_id=1 GROUP BY 1
        """)).all())
        index_valid = db.execute(text("""
            SELECT i.indisvalid AND i.indisunique FROM pg_index i
            JOIN pg_class c ON c.oid=i.indexrelid
            WHERE c.relname='ix_raw_secop_fuente_socrata_row_id'
        """)).scalar_one()
        if not index_valid:
            raise RuntimeError("The source row identity index is missing or invalid")

        headers = {"Accept": "application/json"}
        if adapter.api_key:
            headers["X-App-Token"] = adapter.api_key
        try:
            remote_year_rows = adapter._request_json(headers, {
                "$select": "date_extract_y(fecha_de_publicacion_del) as anio,count(*) as filas",
                "$group": "anio",
                "$order": "anio",
            })
        finally:
            adapter.close()
        remote_years = {
            str(row.get("anio") or "SIN_FECHA"): int(row["filas"])
            for row in remote_year_rows
        }
        after = adapter.probe_generation(sample)
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "database": args.database,
        "source_signature_before": before,
        "source_signature_after": after,
        "local_total": local_total,
        "local_missing_socrata_ids": local_missing_ids,
        "local_unique_index_valid": bool(index_valid),
        "local_by_publication_year": local_years,
        "official_by_publication_year": remote_years,
    }
    report["complete"] = (
        before == after
        and local_total == before["filas"]
        and local_missing_ids == 0
        and {key: int(value) for key, value in local_years.items()} == remote_years
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"coverage_complete={report['complete']} local={local_total} official={before['filas']}")
    if not report["complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
