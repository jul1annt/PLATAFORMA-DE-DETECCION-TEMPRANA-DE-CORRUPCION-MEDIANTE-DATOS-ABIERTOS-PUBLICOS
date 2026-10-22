"""Resume a bounded, checkpointed SECOP history load into a local test database.

This command is deliberately restricted to named, dedicated loopback databases.
It never changes source credentials or starts a second source with the same
public endpoint.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

from dotenv import load_dotenv


SECONDARY_RAW_INDEXES = {
    "ix_raw_secop_id_proceso": "id_del_proceso",
    "ix_raw_secop_fecha_pub": "fecha_de_publicacion_del",
    "ix_raw_secop_nit_entidad": "nit_entidad",
    "ix_raw_secop_entidad": "entidad",
    "ix_raw_secop_estado": "estado_del_procedimiento",
    "ix_raw_secop_modalidad": "modalidad_de_contratacion",
    "ix_raw_secop_fuente": "fuente_id",
    "ix_raw_secop_entidad_fecha": "nit_entidad, fecha_de_publicacion_del",
    "ix_raw_secop_adjudicado": "adjudicado, valor_total_adjudicacion",
}
ALLOWED_DATABASES = {
    "plataforma_backfill_rows_test",
    "plataforma_secop_refresh_test",
    "plataforma_secop_refresh_20261001_test",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, choices=sorted(ALLOWED_DATABASES))
    parser.add_argument("--port", type=int, default=5433)
    parser.add_argument("--source-id", type=int, default=1)
    parser.add_argument("--max-batches", type=int, default=0,
                        help="0 sigue hasta completar la ventana o alcanzar el umbral de disco")
    parser.add_argument("--min-free-gb", type=int, default=20)
    parser.add_argument(
        "--defer-secondary-indexes",
        action="store_true",
        help="reconstruye los índices de consulta al terminar para acelerar la carga",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.database not in ALLOWED_DATABASES:
        raise SystemExit("Base rechazada: use únicamente una base SECOP de ensayo autorizada")
    if args.port != 5433:
        raise SystemExit("Puerto rechazado: la copia de ensayo debe usar 5433")
    if args.source_id != 1:
        raise SystemExit("Fuente rechazada: la carga histórica usa únicamente SECOP II (id 1)")
    if args.max_batches < 0 or args.min_free_gb < 1:
        raise SystemExit("Los límites deben ser positivos")

    backend_dir = Path(__file__).resolve().parents[1]
    load_dotenv(backend_dir / ".env")
    sys.path.insert(0, str(backend_dir))
    os.environ.update(
        DB_HOST="127.0.0.1",
        DB_PORT=str(args.port),
        DB_NAME=args.database,
        INGESTA_MAX_RECORDS_PER_SYNC="100000",
    )

    from sqlalchemy import text

    from core.database import SessionLocal
    from core.database import engine
    from modules.ingesta.model.FuenteDatos import FuenteDatos
    from modules.jobs.model import BackgroundJob
    from modules.jobs.service import enqueue_job
    from modules.jobs.worker import process_next_job

    with SessionLocal() as db:
        identity = db.execute(text(
            "SELECT current_database(), inet_server_addr()::text, "
            "current_setting('data_directory')"
        )).one()
        if identity[0] != args.database or not identity[1].startswith("127.0.0.1/"):
            raise SystemExit("Conexión rechazada: el servidor no coincide con la copia local esperada")
        source = db.query(FuenteDatos).filter(FuenteDatos.id == args.source_id).one()
        if source.nombre != "SECOP II" or not source.endpoint.endswith("/p6dx-8zbt.json"):
            raise SystemExit("Fuente rechazada: el id 1 no corresponde al conjunto SECOP II esperado")
        data_dir = Path(identity[2])

    def set_secondary_indexes(enabled: bool) -> None:
        with engine.begin() as connection:
            for name, columns in SECONDARY_RAW_INDEXES.items():
                if enabled:
                    connection.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {name} ON raw_secop ({columns})"
                    ))
                else:
                    connection.execute(text(f"DROP INDEX IF EXISTS {name}"))
            if enabled:
                connection.execute(text("ANALYZE raw_secop"))

    indexes_deferred = False
    try:
        if args.defer_secondary_indexes:
            with SessionLocal() as db:
                active = db.query(BackgroundJob.id).filter(
                    BackgroundJob.active.is_(True),
                ).first()
                if active:
                    raise SystemExit(f"No se difieren índices con trabajos activos: {active.id}")
            indexes_deferred = True
            set_secondary_indexes(False)
            print("secondary_indexes=deferred", flush=True)

        start = time.monotonic()
        completed_batches = 0
        min_free_bytes = args.min_free_gb * 1024**3
        while True:
            free_bytes = shutil.disk_usage(data_dir).free
            if free_bytes < min_free_bytes:
                print(f"stopped=low_disk free_gb={free_bytes / 1024**3:.1f}", flush=True)
                return 2
            with SessionLocal() as db:
                active = db.query(BackgroundJob).filter(
                    BackgroundJob.active.is_(True),
                    BackgroundJob.resource_key == f"ingesta:{args.source_id}",
                ).first()
                pending = db.query(BackgroundJob.id).filter(
                    BackgroundJob.status == "PENDIENTE",
                    BackgroundJob.active.is_(True),
                ).all()
                if active:
                    raise SystemExit(f"Trabajo activo preexistente para SECOP II: {active.id}")
                if pending:
                    raise SystemExit(f"Hay trabajos pendientes ajenos a esta carga: {pending}")
                job, created = enqueue_job(
                    db,
                    kind="INGESTA",
                    payload={"fuente_id": args.source_id},
                    resource_key=f"ingesta:{args.source_id}",
                )
                if not created:
                    raise SystemExit("No se pudo crear un trabajo nuevo para SECOP II")
                job_id = job.id

            if not process_next_job():
                raise SystemExit("El worker no pudo reclamar el trabajo recién creado")

            with SessionLocal() as db:
                job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).one()
                result = job.result or {}
                checkpoint = result.get("checkpoint") or {}
                print(
                    "batch={} status={} fetched={} inserted={} cursor={} "
                    "window_rows={} elapsed_s={:.1f} free_gb={:.1f}".format(
                        job_id,
                        job.status,
                        result.get("registros_traidos", 0),
                        result.get("registros_insertados", 0),
                        checkpoint.get("last_id"),
                        checkpoint.get("window_rows", 0),
                        time.monotonic() - start,
                        shutil.disk_usage(data_dir).free / 1024**3,
                    ),
                    flush=True,
                )
                status = job.status
                partial = result.get("parcial") is True

            completed_batches += 1
            if status == "ERROR":
                print("stopped=job_error; checkpoint retained for manual resume", flush=True)
                return 1
            if result.get("replacement_detected") or result.get("source_changed") or result.get("identity_unverifiable"):
                print("stopped=source_generation_changed; no automatic retry", flush=True)
                return 3
            if not partial:
                print("completed=full_window", flush=True)
                return 0
            if args.max_batches and completed_batches >= args.max_batches:
                print("stopped=max_batches; checkpoint retained", flush=True)
                return 0
    finally:
        if indexes_deferred:
            set_secondary_indexes(True)
            print("secondary_indexes=restored", flush=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("stopped=interrupted; last committed checkpoint is retained", flush=True)
        raise SystemExit(130)
