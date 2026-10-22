"""Compare legacy raw rows with the full SECOP clone without changing either database.

The legacy snapshot predates Socrata row IDs. Process IDs therefore select
candidate rows only; matching is evaluated on all source fields and on a
separate, explicitly non-authoritative award comparison tuple.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import settings  # noqa: E402

REPORT_PATH = ROOT.parent / "docs" / "auditoria" / "RECONCILIACION_SUBCONJUNTO_LEGACY.json"
LEGACY_DB = "plataforma_cutover_restore_check"
CURRENT_DB = "plataforma_cutover_test"
EXCLUDED_FROM_VALUE_MATCH = {"id", "socrata_row_id", "sincronizado_en"}
AWARD_COMPARISON_FIELDS = (
    "fuente_id",
    "id_del_proceso",
    "id_adjudicacion",
    "codigoproveedor",
    "nit_del_proveedor_adjudicado",
    "valor_total_adjudicacion",
)


def make_engine(database: str):
    configured_url = make_url(settings.DATABASE_URL)
    if configured_url.host not in {"127.0.0.1", "localhost"} or configured_url.port not in {5432, 5433}:
        raise RuntimeError("La configuración del proyecto no apunta a PostgreSQL local; se cancela el cotejo.")
    # This report is deliberately restricted to the two isolated local databases.
    pinned_url = configured_url.set(
        host="127.0.0.1", port=5433, database=database
    )
    if pinned_url.host != "127.0.0.1" or pinned_url.port != 5433:
        raise RuntimeError("La reconciliación solo se permite en el clon aislado local.")
    return create_engine(pinned_url, connect_args={"connect_timeout": 10}, pool_pre_ping=True)


def read_only_transaction(engine):
    connection = engine.connect()
    connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
    return connection


def source_columns(connection) -> list[str]:
    return list(
        connection.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='raw_secop' "
                "ORDER BY ordinal_position"
            )
        ).scalars()
    )


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def main() -> None:
    legacy_engine = make_engine(LEGACY_DB)
    current_engine = make_engine(CURRENT_DB)
    try:
        with read_only_transaction(legacy_engine) as connection:
            legacy_columns = source_columns(connection)
            required = {"id", "socrata_row_id", "id_del_proceso", *AWARD_COMPARISON_FIELDS}
            if not required.issubset(legacy_columns):
                raise RuntimeError(f"Faltan columnas requeridas en el snapshot heredado: {sorted(required - set(legacy_columns))}")
            fields = [column for column in legacy_columns if column not in EXCLUDED_FROM_VALUE_MATCH]
            projection = ", ".join(quote_identifier(c) for c in ["id", "socrata_row_id", *fields])
            legacy_rows = connection.execute(
                text(f"SELECT {projection} FROM public.raw_secop ORDER BY id")
            ).mappings().all()
            connection.commit()

        by_process: dict[str, list[tuple[int, tuple]]] = defaultdict(list)
        for row in legacy_rows:
            if row["id_del_proceso"] is not None:
                by_process[row["id_del_proceso"]].append(
                    (row["id"], tuple(row[column] for column in fields))
                )
        process_ids = list(by_process)
        if not process_ids:
            raise RuntimeError("El snapshot heredado no contiene IDs de proceso que comparar.")

        with read_only_transaction(current_engine) as connection:
            current_columns = set(source_columns(connection))
            if not set(fields).issubset(current_columns):
                raise RuntimeError("Las columnas fuente de ambas bases no son compatibles.")
            # The indexed process-ID lookup restricts reads to candidate rows. The
            # source row ID is deliberately not inferred from a process ID.
            connection.exec_driver_sql("SET LOCAL enable_seqscan=off")
            current_rows = connection.execute(
                text(
                    "SELECT " + ", ".join(quote_identifier(c) for c in fields)
                    + " FROM public.raw_secop WHERE id_del_proceso = ANY(:process_ids)"
                ),
                {"process_ids": process_ids},
            ).mappings().all()
            connection.commit()

        candidates_by_process: dict[str, list[tuple]] = defaultdict(list)
        for row in current_rows:
            candidates_by_process[row["id_del_proceso"]].append(
                tuple(row[column] for column in fields)
            )

        field_index = {column: index for index, column in enumerate(fields)}
        award_fields = [column for column in AWARD_COMPARISON_FIELDS if column in field_index]

        def award_key(signature: tuple) -> tuple:
            return tuple(signature[field_index[column]] for column in award_fields)

        exact_cardinality = Counter()
        award_cardinality = Counter()
        nearest_award_key_field_differences = Counter()
        nearest_award_key_field_change_kinds = Counter()
        same_award_key_but_changed = 0

        for process_id, legacy_items in by_process.items():
            candidates = candidates_by_process.get(process_id, [])
            for _legacy_id, old_signature in legacy_items:
                exact_candidates = [candidate for candidate in candidates if candidate == old_signature]
                exact_cardinality[len(exact_candidates)] += 1

                old_award_key = award_key(old_signature)
                award_candidates = [candidate for candidate in candidates if award_key(candidate) == old_award_key]
                award_cardinality[len(award_candidates)] += 1
                if award_candidates and not exact_candidates:
                    same_award_key_but_changed += 1
                    distances = [
                        sum(old_value != new_value for old_value, new_value in zip(old_signature, candidate))
                        for candidate in award_candidates
                    ]
                    closest = min(distances)
                    for candidate, distance in zip(award_candidates, distances):
                        if distance == closest:
                            for column, old_value, new_value in zip(fields, old_signature, candidate):
                                if old_value == new_value:
                                    continue
                                nearest_award_key_field_differences[column] += 1
                                if old_value is None:
                                    kind = "legacy_null_current_populated"
                                elif new_value is None:
                                    kind = "legacy_populated_current_null"
                                else:
                                    kind = "both_populated_different"
                                nearest_award_key_field_change_kinds[(column, kind)] += 1

        legacy_row_count = len(legacy_rows)
        current_process_set = set(candidates_by_process)
        legacy_process_set = set(by_process)
        exact_unique = exact_cardinality[1]
        exact_ambiguous = sum(count for cardinality, count in exact_cardinality.items() if cardinality > 1)
        exact_missing = exact_cardinality[0]
        award_unique = award_cardinality[1]
        award_ambiguous = sum(count for cardinality, count in award_cardinality.items() if cardinality > 1)
        award_missing = award_cardinality[0]

        report = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "legacy_database": LEGACY_DB,
            "current_database": CURRENT_DB,
            "method": {
                "candidate_lookup": "id_del_proceso; candidate selector only, not a row identity",
                "full_value_match_fields": len(fields),
                "full_value_match_excludes": sorted(EXCLUDED_FROM_VALUE_MATCH),
                "award_comparison_tuple": award_fields,
                "award_tuple_is_authoritative_identity": False,
                "closest_field_counts_include_tied_candidates": True,
                "closest_field_counts_are_diagnostic_only": True,
                "write_operations": 0,
            },
            "counts": {
                "legacy_rows": legacy_row_count,
                "legacy_rows_with_socrata_row_id": sum(row["socrata_row_id"] is not None for row in legacy_rows),
                "legacy_rows_without_process_id": sum(row["id_del_proceso"] is None for row in legacy_rows),
                "legacy_process_ids": len(legacy_process_set),
                "legacy_process_ids_found_in_current": len(legacy_process_set & current_process_set),
                "legacy_process_ids_absent_from_current": len(legacy_process_set - current_process_set),
                "current_candidate_rows_for_legacy_process_ids": len(current_rows),
                "legacy_process_ids_with_multiple_current_rows": sum(
                    len(candidates_by_process[process_id]) > 1 for process_id in legacy_process_set
                ),
                "exact_full_source_row_matches_unique": exact_unique,
                "exact_full_source_row_matches_ambiguous": exact_ambiguous,
                "exact_full_source_row_without_match": exact_missing,
                "award_tuple_matches_unique": award_unique,
                "award_tuple_matches_ambiguous": award_ambiguous,
                "award_tuple_without_match": award_missing,
                "award_tuple_match_but_other_fields_differ": same_award_key_but_changed,
            },
            "closest_candidate_field_difference_counts": dict(
                nearest_award_key_field_differences.most_common(20)
            ),
            "closest_candidate_field_difference_types": [
                {
                    "field": column,
                    "legacy_null_current_populated": nearest_award_key_field_change_kinds[(column, "legacy_null_current_populated")],
                    "legacy_populated_current_null": nearest_award_key_field_change_kinds[(column, "legacy_populated_current_null")],
                    "both_populated_different": nearest_award_key_field_change_kinds[(column, "both_populated_different")],
                }
                for column, _count in nearest_award_key_field_differences.most_common(20)
            ],
            "interpretation": (
                "Legacy rows have no Socrata row ID. Exact field matches are strong content evidence, "
                "but rows with duplicate matches, changed attributes, or no award-tuple match are not "
                "assigned an inferred source-row identity."
            ),
        }
        if legacy_row_count != (
            exact_unique + exact_ambiguous + exact_missing
        ) or legacy_row_count != award_unique + award_ambiguous + award_missing:
            raise RuntimeError("Los grupos de comparación no cubren exactamente las filas heredadas.")

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"Informe agregado: {REPORT_PATH}")
    finally:
        legacy_engine.dispose()
        current_engine.dispose()


if __name__ == "__main__":
    main()
