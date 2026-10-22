"""Bounded-memory diagnostic contexts; never historical stage reconstruction."""
from sqlalchemy import text
from .materialize import prepare_capture
from .rolling_materialize import prepare_rolling_context
from .annual_materialize import prepare_annual_context


def prepare_context(db, source_ids: list[int], at: str):
    db.execute(text("SET LOCAL work_mem='32MB'"))
    db.execute(text("SET LOCAL statement_timeout='600s'"))
    db.execute(text('SET LOCAL max_parallel_workers_per_gather=0'))
    db.execute(text('DROP TABLE IF EXISTS pg_temp.risk_history'))
    captured = prepare_capture(db, source_ids)
    prepare_rolling_context(db, at)
    prepare_annual_context(db, at)
    db.commit()
    return captured
