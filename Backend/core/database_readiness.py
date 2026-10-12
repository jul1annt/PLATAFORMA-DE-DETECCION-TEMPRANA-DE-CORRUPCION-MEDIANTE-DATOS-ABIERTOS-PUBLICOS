"""Prepare local PostgreSQL connections before accepting HTTP requests."""
from concurrent.futures import ThreadPoolExecutor
from ipaddress import ip_address
from threading import Barrier

from sqlalchemy import text


def prepare_database_pool(engine, count: int) -> int:
    if not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= 10:
        raise ValueError("La cantidad de conexiones debe estar entre cero y diez")
    if count == 0:
        return 0
    if (
        engine.url.get_backend_name() != "postgresql"
        or engine.url.host not in {"127.0.0.1", "localhost", "::1"}
        or count > engine.pool.size()
    ):
        raise ValueError("La preparación requiere un pool PostgreSQL local suficiente")
    barrier = Barrier(count)

    def prepare_one(_):
        try:
            with engine.connect() as connection:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                connection.execute(text("SET LOCAL statement_timeout=5000"))
                row = connection.execute(text(
                    "SELECT current_database() AS database, current_user AS role, "
                    "host(inet_server_addr()) AS address, inet_server_port() AS port, "
                    "pg_backend_pid() AS pid, rolsuper, rolcreatedb, rolcreaterole, rolreplication "
                    "FROM pg_roles WHERE rolname=current_user"
                )).mappings().one()
                if (
                    row["database"] != engine.url.database
                    or row["role"] != engine.url.username
                    or row["port"] != (engine.url.port or 5432)
                    or not ip_address(row["address"]).is_loopback
                    or any(row[key] for key in ("rolsuper", "rolcreatedb", "rolcreaterole", "rolreplication"))
                ):
                    raise ValueError("La conexión no cumple la identidad y privilegios locales")
                # Hold every connection concurrently so no prepared slot is
                # counted repeatedly by borrowing the same idle connection.
                barrier.wait(timeout=70)
                return row["pid"]
        except Exception:
            barrier.abort()
            raise RuntimeError("No se completó la preparación del pool local") from None

    with ThreadPoolExecutor(max_workers=count) as workers:
        pids = list(workers.map(prepare_one, range(count)))
    if len(set(pids)) != count:
        raise RuntimeError("Las conexiones preparadas no son independientes")
    return count
