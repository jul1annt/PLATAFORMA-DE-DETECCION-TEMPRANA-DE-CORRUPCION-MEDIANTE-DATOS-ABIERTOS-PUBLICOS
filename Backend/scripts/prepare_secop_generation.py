"""Prepare a new isolated database for the detected 2026-10-01 SECOP generation."""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "plataforma_secop_refresh_test"
TARGET = "plataforma_secop_refresh_20261001_test"
load_dotenv(ROOT / ".env")
os.environ.update(DB_HOST="127.0.0.1", DB_PORT="5433", DB_NAME=SOURCE)
sys.path.insert(0, str(ROOT))

from core.config import settings  # noqa: E402
from modules.ingesta.model.FuenteDatos import FuenteDatos  # noqa: E402


def main() -> None:
    url = make_url(settings.DATABASE_URL)
    if (url.host, url.port, url.database) != ("127.0.0.1", 5433, SOURCE):
        raise RuntimeError("Source database guard failed")
    source_engine = create_engine(url, connect_args={"connect_timeout": 10})
    maintenance = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    target_engine = create_engine(url.set(database=TARGET), connect_args={"connect_timeout": 10})
    try:
        with Session(source_engine) as db:
            identity = db.execute(text("SELECT current_database(), current_setting('data_directory')")).one()
            if identity[0] != SOURCE or "recovery-clone-20260929" not in identity[1]:
                raise RuntimeError("Source cluster guard failed")
            source = db.query(FuenteDatos).filter(FuenteDatos.id == 1).one()
            if source.tipo != "SECOP" or not source.endpoint.endswith("/p6dx-8zbt.json"):
                raise RuntimeError("SECOP source guard failed")
            source_data = {
                "id": source.id, "nombre": source.nombre, "tipo": source.tipo,
                "formato": source.formato, "endpoint": source.endpoint,
                "api_key": source.api_key, "frecuencia_dias": source.frecuencia_dias,
                "activo": source.activo,
            }
        with maintenance.connect() as db:
            exists = db.execute(text("SELECT 1 FROM pg_database WHERE datname=:name"), {"name": TARGET}).first()
            if not exists:
                owner = db.execute(text("SELECT current_user")).scalar_one()
                if owner != "postgres":
                    raise RuntimeError("Unexpected database owner")
                db.exec_driver_sql(f'CREATE DATABASE "{TARGET}" OWNER "{owner}"')
                print(f"created={TARGET}", flush=True)
        env = os.environ.copy()
        env["DB_NAME"] = TARGET
        result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                                cwd=ROOT, env=env, check=False)
        if result.returncode:
            raise RuntimeError(f"Alembic failed with exit code {result.returncode}")
        with Session(target_engine) as db:
            identity = db.execute(text("SELECT current_database(), current_setting('data_directory')")).one()
            if identity[0] != TARGET or "recovery-clone-20260929" not in identity[1]:
                raise RuntimeError("Target cluster guard failed")
            existing = db.query(FuenteDatos).filter(FuenteDatos.id == 1).first()
            if existing:
                if (existing.nombre, existing.tipo, existing.endpoint) != (
                    source_data["nombre"], source_data["tipo"], source_data["endpoint"]
                ):
                    raise RuntimeError("Existing source does not match SECOP II")
                print(f"ready={TARGET} existing_source=true", flush=True)
                return
            if db.execute(text("SELECT EXISTS (SELECT 1 FROM raw_secop)")).scalar_one():
                raise RuntimeError("Target has raw data without a configured source")
            db.add(FuenteDatos(**source_data, ultima_sync=None))
            db.commit()
            print(f"ready={TARGET} source=SECOP II watermark=null", flush=True)
    finally:
        source_engine.dispose()
        maintenance.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    main()
