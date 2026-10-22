"""Optional request-scoped PostgreSQL policy for expensive public reads.

The nested get_db dependency owns the session and closes it on every outcome.
SET LOCAL disappears on commit/rollback, including pooled connection return.
Workers and metric routes continue to use their normal database dependency.
"""

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db


def apply_read_parallelism(db: Session, workers: int | None) -> Session:
    if workers is None:
        return db
    if isinstance(workers, bool) or not isinstance(workers, int) or not 0 <= workers <= 1024:
        raise ValueError("Read query worker limit must be an integer from 0 to 1024")
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text("SELECT set_config('max_parallel_workers_per_gather', :workers, true)"),
            {"workers": str(workers)},
        )
    return db


def get_search_db(db: Session = Depends(get_db)) -> Session:
    return apply_read_parallelism(db, settings.SEARCH_QUERY_PARALLEL_WORKERS)


def get_provider_db(db: Session = Depends(get_db)) -> Session:
    return apply_read_parallelism(db, settings.PROVIDER_QUERY_PARALLEL_WORKERS)
