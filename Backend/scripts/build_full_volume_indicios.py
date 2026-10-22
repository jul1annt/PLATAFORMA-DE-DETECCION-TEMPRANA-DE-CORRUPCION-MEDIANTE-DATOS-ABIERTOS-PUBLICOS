"""Build an isolated, read-only IQR indication snapshot for every contract.

Capture is keyset-paged by the source primary key in one repeatable-read,
read-only transaction. Percentiles and results are calculated in a separate
SQLite work file; PostgreSQL tables are never written.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.config import settings
from modules.motor_riesgo.baseline_coverage import baseline_coverage
from modules.motor_riesgo.rules import iqr_finding_from_reference

OUT = ROOT / ".codex-analytics-postgres" / "mvp-risk-20261020"
TARGET = OUT / "full-volume-v3.sqlite"
TEMP = OUT / "full-volume-v3.sqlite.partial"
EXPECTED_ROWS = 9_249_545
BATCH_SIZE = 5_000
REPORT_EVERY = 100_000
INSERT_BATCH = 5_000
RESULT_BATCH = 50_000

CAPTURE_QUERY = text("""
SELECT id, raw_secop_id, NULLIF(BTRIM(id_del_proceso), ''),
       entidad_normalizada, proveedor_normalizado,
       fecha_publicacion_normalizada,
       tipo_contrato_normalizado, modalidad_contratacion,
       precio_base_normalizado::text, precio_base_normalizado::double precision,
       valor_total_normalizado::text, fecha_adjudicacion_normalizada,
       urlproceso, es_sospechoso
FROM public.contratos_procesados
WHERE id > :after_id
ORDER BY id
LIMIT :limit
""")

RAW_INSERT = "INSERT INTO raw VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
RESULT_INSERT = "INSERT INTO results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"


def iso(value):
    return value.isoformat() if value is not None else None


def positive_decimal(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() and parsed > 0 else None


def json_text(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str, allow_nan=False)


def quantile(sorted_values, probability):
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def build_finding(process_id, process_rows, published_at, contract_type, modality,
                  amount, peers, q1, q3):
    original = positive_decimal(amount)
    reference = {"indicator": "IMPORTE_ATIPICO", "reference": "OCP_RED_FLAGS_IQR",
                 "n": int(peers or 0), "detected": None}
    if not process_id:
        reason = "identidad_de_proceso_ausente"
    elif process_rows != 1:
        reason = "identidad_de_proceso_ambigua"
    elif published_at is None or not str(contract_type or "").strip() or not str(modality or "").strip():
        reason = "periodo_tipo_o_modalidad_ausente"
    elif original is None:
        reason = "importe_ausente_o_invalido"
    elif peers is None or peers < 30:
        reason = "grupo_insuficiente"
    elif q1 is None or q3 is None or Decimal(str(q3)) <= Decimal(str(q1)):
        reason = "iqr_cero"
    else:
        reason = None

    if reason:
        reference["reason"] = reason
        return iqr_finding_from_reference(amount, reference)
    first, third = Decimal(str(q1)), Decimal(str(q3))
    spread = third - first
    reference.update({"q1": first, "q3": third,
                      "lower": first - Decimal("1.5") * spread,
                      "upper": third + Decimal("1.5") * spread})
    return iqr_finding_from_reference(amount, reference)


def make_coverage(stage, modality, finding):
    return baseline_coverage({"modalidad": modality, "oferentes": None,
                              "directas_90d": None, "reiteraciones_30d": None}, stage, finding)


def create_iqr_strata(db):
    db.execute("CREATE INDEX IF NOT EXISTS ix_raw_stratum_amount_process ON raw(comparison_period,contract_type,modality,amount_real,process_id)")
    db.commit()
    unique_process_ids = {row[0] for row in db.execute(
        "SELECT process_id FROM process_counts WHERE row_count=1")}
    print(json.dumps({"phase": "iqr_unique_processes", "count": len(unique_process_ids)}), flush=True)
    source = db.execute("""
        SELECT r.process_id,r.comparison_period,r.contract_type,r.modality,r.amount_real
        FROM raw r INDEXED BY ix_raw_stratum_amount_process
        WHERE r.comparison_period IS NOT NULL
          AND NULLIF(TRIM(r.contract_type),'') IS NOT NULL
          AND NULLIF(TRIM(r.modality),'') IS NOT NULL
          AND r.amount_real>0
        ORDER BY r.comparison_period,r.contract_type,r.modality,r.amount_real,r.process_id
    """)
    group_key = None
    amounts = []
    strata_rows = []
    read_rows = 0

    def save_group(key, group_amounts):
        if key is None:
            return
        q1 = quantile(group_amounts, .25) if group_amounts else None
        q3 = quantile(group_amounts, .75) if group_amounts else None
        strata_rows.append((*key, len(group_amounts), q1, q3))
        if len(strata_rows) >= INSERT_BATCH:
            db.executemany("INSERT INTO strata VALUES (?,?,?,?,?,?)", strata_rows)
            db.commit(); strata_rows.clear()

    for process_id, period, contract_type, modality, amount in source:
        read_rows += 1
        if process_id is None or process_id not in unique_process_ids:
            continue
        key = (period, contract_type, modality)
        if key != group_key:
            save_group(group_key, amounts)
            group_key = key
            amounts = []
        amounts.append(float(amount))
        if read_rows % 500_000 == 0:
            print(json.dumps({"phase": "iqr_reference_progress", "rows": read_rows}), flush=True)
    save_group(group_key, amounts)
    if strata_rows:
        db.executemany("INSERT INTO strata VALUES (?,?,?,?,?,?)", strata_rows)
        db.commit(); strata_rows.clear()
    source.close()
    return db.execute("SELECT COUNT(*) FROM strata").fetchone()[0]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if TARGET.exists():
        raise SystemExit(f"Ya existe un corte full-volume v3: {TARGET.name}")
    resume = TEMP.exists()

    engine = None
    conn = None
    if resume:
        # The full source capture was already verified before the interrupted
        # local inference. Do not rescan PostgreSQL just to resume local work.
        snapshot = "no reabierto en reanudacion"
        source_count = EXPECTED_ROWS
    else:
        engine = create_engine(
            settings.DATABASE_URL,
            pool_size=1,
            max_overflow=0,
            connect_args={"connect_timeout": 30,
                          "options": "-c default_transaction_read_only=on -c statement_timeout=0"},
        )
        conn = engine.connect().execution_options(isolation_level="REPEATABLE READ")
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        conn.exec_driver_sql("SET LOCAL statement_timeout = 0")
        snapshot = conn.execute(text("SELECT txid_current_snapshot()::text")).scalar_one()
        source_count = conn.execute(text("SELECT COUNT(*) FROM public.contratos_procesados")).scalar_one()
        if source_count != EXPECTED_ROWS:
            conn.rollback()
            conn.close()
            engine.dispose()
            raise SystemExit(f"Corte no esperado: PostgreSQL informa {source_count:,}; se esperaba {EXPECTED_ROWS:,}.")

    db = sqlite3.connect(TEMP)
    db.execute(f"PRAGMA journal_mode={'WAL' if resume else 'DELETE'}")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA temp_store=FILE")
    db.execute(f"PRAGMA cache_size={-524288 if resume else -131072}")
    if not resume:
        db.executescript("""
        CREATE TABLE raw (
            id INTEGER PRIMARY KEY,
            raw_secop_id INTEGER NOT NULL UNIQUE,
            process_id TEXT,
            entity TEXT,
            supplier TEXT,
            published_at TEXT,
            contract_type TEXT,
            modality TEXT,
            amount TEXT,
            amount_real REAL,
            award_amount TEXT,
            award_date TEXT,
            source_url TEXT,
            legacy_data_quality_flag INTEGER NOT NULL,
            comparison_period TEXT
        );
        CREATE TABLE process_counts (process_id TEXT PRIMARY KEY, row_count INTEGER NOT NULL) WITHOUT ROWID;
        CREATE TABLE strata (
            period TEXT NOT NULL,
            contract_type TEXT NOT NULL,
            modality TEXT NOT NULL,
            peers INTEGER NOT NULL,
            q1 REAL,
            q3 REAL,
            PRIMARY KEY (period, contract_type, modality)
        ) WITHOUT ROWID;
        CREATE TABLE results (
            id INTEGER PRIMARY KEY,
            raw_secop_id INTEGER NOT NULL UNIQUE,
            process_id TEXT,
            entity TEXT,
            supplier TEXT,
            published_at TEXT,
            contract_type TEXT,
            modality TEXT,
            amount TEXT,
            award_amount TEXT,
            stage TEXT NOT NULL,
            comparison_period TEXT,
            source_url TEXT,
            signal INTEGER,
            status TEXT NOT NULL,
            evidence TEXT NOT NULL,
            coverage TEXT NOT NULL,
            missing_evidence TEXT NOT NULL,
            legacy_data_quality_flag INTEGER NOT NULL
        );
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)

    started = time.monotonic()
    captured = 0
    last_id = 0
    digest = hashlib.sha256()
    try:
        if resume:
            # This partial was created from a completed, validated capture.
            # Avoid rescanning 9.2M rows merely to rediscover its row count.
            captured = source_count
            print(json.dumps({"phase": "resume_local_capture", "rows": captured,
                              "snapshot_id_retained": False}), flush=True)
            hashed = 0
            for raw_id, process_id, published, contract_type, modality, amount in db.execute(
                    "SELECT raw_secop_id,process_id,published_at,contract_type,modality,amount FROM raw ORDER BY id"):
                canonical = json_text([raw_id, process_id, published, contract_type, modality, amount])
                digest.update(canonical.encode("utf-8")); digest.update(b"\n")
                hashed += 1
                if hashed % 500_000 == 0:
                    print(json.dumps({"phase": "resume_hash", "rows": hashed,
                                      "total": captured}), flush=True)
        else:
            print(json.dumps({"phase": "capture_started", "source_rows": source_count,
                              "source_snapshot": snapshot}), flush=True)
            while True:
                rows = conn.execute(CAPTURE_QUERY, {"after_id": last_id, "limit": BATCH_SIZE}).fetchall()
                if not rows:
                    break
                values = []
                for row in rows:
                    row_id, raw_id, process_id, entity, supplier, published, contract_type, modality, amount, amount_real, award_amount, award_date, source_url, legacy = row
                    published = iso(published)
                    award_date = iso(award_date)
                    amount_text = str(amount) if amount is not None else None
                    canonical = json_text([raw_id, process_id, published, contract_type, modality, amount_text])
                    digest.update(canonical.encode("utf-8")); digest.update(b"\n")
                    values.append((row_id, raw_id, process_id, entity, supplier, published, contract_type, modality,
                                   amount_text, amount_real, award_amount, award_date, source_url, int(bool(legacy)),
                                   published[:7] if published else None))
                db.executemany(RAW_INSERT, values)
                db.commit()
                captured += len(rows)
                last_id = rows[-1][0]
                if captured % REPORT_EVERY == 0 or captured == source_count:
                    elapsed = max(time.monotonic() - started, 0.001)
                    print(json.dumps({"phase": "capture", "rows": captured,
                                      "total": source_count,
                                      "rows_per_second": round(captured / elapsed, 1)}), flush=True)

        if captured != source_count:
            raise RuntimeError(f"Captura incompleta: {captured:,} de {source_count:,} filas")
        local_count = db.execute("SELECT COUNT(*) FROM raw").fetchone()[0]
        id_count = db.execute("SELECT COUNT(DISTINCT raw_secop_id) FROM raw").fetchone()[0]
        if local_count != source_count or id_count != source_count:
            raise RuntimeError(f"Corte local inválido: filas={local_count:,}, IDs={id_count:,}, origen={source_count:,}")

        if not resume:
            print(json.dumps({"phase": "process_identity_counts", "rows": captured}), flush=True)
            db.execute("INSERT INTO process_counts(process_id,row_count) SELECT process_id,COUNT(*) FROM raw WHERE process_id IS NOT NULL GROUP BY process_id")
            db.commit()
            db.execute("CREATE INDEX ix_raw_stratum_amount ON raw(comparison_period,contract_type,modality,amount_real)")
            db.commit()
        else:
            if not db.execute("SELECT COUNT(*) FROM process_counts").fetchone()[0]:
                raise RuntimeError("No se encontró el conteo de identidades en el parcial")

        strata_count = db.execute("SELECT COUNT(*) FROM strata").fetchone()[0]
        if strata_count == 0:
            print(json.dumps({"phase": "iqr_reference", "rows": captured}), flush=True)
            strata_count = create_iqr_strata(db)
        else:
            print(json.dumps({"phase": "iqr_reference_reused", "groups": strata_count}), flush=True)
        db.execute("CREATE INDEX IF NOT EXISTS ix_raw_process_id ON raw(process_id)")
        db.commit()

        print(json.dumps({"phase": "infer_and_store", "rows": captured,
                          "strata": strata_count}), flush=True)
        existing_results = db.execute("SELECT COALESCE(MAX(id),0) FROM results").fetchone()[0]
        cursor = db.execute("""
            SELECT r.id,r.raw_secop_id,r.process_id,r.entity,r.supplier,r.published_at,
                   r.contract_type,r.modality,r.amount,r.award_amount,r.award_date,
                   r.source_url,r.legacy_data_quality_flag,COALESCE(p.row_count,0),
                   s.peers,s.q1,s.q3
            FROM raw r
            LEFT JOIN process_counts p ON p.process_id=r.process_id
            LEFT JOIN strata s ON s.period=r.comparison_period
                              AND s.contract_type=r.contract_type
                              AND s.modality=r.modality
            WHERE r.id > COALESCE((SELECT MAX(id) FROM results),0)
            ORDER BY r.id
        """)
        batch = []
        processed = existing_results
        for row in cursor:
            finding = build_finding(row[2], row[13], row[5], row[6], row[7], row[8], row[14], row[15], row[16])
            stage = "ADJUDICACION" if row[10] is not None else "CONVOCATORIA"
            coverage = make_coverage(stage, row[7], finding)
            signal = finding["detected"]
            if signal:
                status = "CON_SENAL_CONFIRMADA"
            elif signal is None and coverage["evaluated_families"] == 0:
                status = "NO_EVALUABLE"
            elif coverage["unevaluable_families"]:
                status = "EVIDENCIA_INSUFICIENTE"
            else:
                status = "SIN_SENAL_OBSERVADA"
            missing = [f"{name}:{indicator['reason'] or 'evidencia_insuficiente'}"
                       for name, indicator in coverage["indicators"].items()
                       if indicator["status"] == "NO_EVALUABLE"]
            batch.append((
                row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9],
                stage,row[5][:7] if row[5] else None,row[11],
                None if signal is None else int(signal),status,json_text(finding),
                json_text(coverage),json_text(missing),int(bool(row[12])),
            ))
            processed += 1
            if len(batch) >= RESULT_BATCH:
                db.executemany(RESULT_INSERT, batch); db.commit(); batch.clear()
            if processed % REPORT_EVERY == 0 or processed == source_count:
                elapsed = max(time.monotonic() - started, 0.001)
                print(json.dumps({"phase": "infer", "rows": processed,
                                  "total": source_count,
                                  "rows_per_second": round(processed / elapsed, 1)}), flush=True)
        cursor.close()
        if batch:
            db.executemany(RESULT_INSERT, batch); db.commit(); batch.clear()
        if processed != source_count:
            raise RuntimeError(f"Inferencia incompleta: {processed:,} de {source_count:,} filas")

        print(json.dumps({"phase": "index_and_publish", "rows": processed}), flush=True)
        db.executescript("""
            CREATE INDEX IF NOT EXISTS ix_results_public_order ON results(signal DESC,published_at DESC,raw_secop_id);
            CREATE INDEX IF NOT EXISTS ix_results_status_stage ON results(status,stage,published_at DESC,raw_secop_id);
            CREATE INDEX IF NOT EXISTS ix_results_type_modality ON results(contract_type,modality,published_at DESC,raw_secop_id);
            CREATE INDEX IF NOT EXISTS ix_results_process_id ON results(process_id);
        """)
        # Keep the census publishable on a local machine with bounded disk space.
        # Search can fall back to SQL LIKE; a full-text index is an optional later build.
        db.execute("DROP TABLE IF EXISTS results_fts")
        db.commit()

        (total, minimum, maximum, signal_count, no_signal_count, no_eval_count,
         partial_count, complete_count, call_count, award_count) = db.execute("""
            SELECT COUNT(*), MIN(published_at), MAX(published_at),
                   SUM(CASE WHEN signal=1 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN signal IS NULL OR signal=0 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status='NO_EVALUABLE' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status='EVIDENCIA_INSUFICIENTE' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status IN ('CON_SENAL_CONFIRMADA','SIN_SENAL_OBSERVADA') THEN 1 ELSE 0 END),
                   SUM(CASE WHEN stage='CONVOCATORIA' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN stage='ADJUDICACION' THEN 1 ELSE 0 END)
              FROM results
        """).fetchone()
        coverage_counts = {
            "signal": signal_count,
            "no_confirmed_signal": no_signal_count,
            "no_evaluable_family": no_eval_count,
            "partial_or_unknown": partial_count,
            "complete_family_evaluation": complete_count,
            "by_stage": {"CONVOCATORIA": call_count, "ADJUDICACION": award_count},
        }
        state = {
            "name": "Motor local de señales de riesgo explicables",
            "status": "MVP_RULES_ONLY",
            "snapshot_cut": settings.RISK_BASELINE_CUT_DATE.isoformat(),
            "cohort": {"start": minimum, "end": maximum, "rows": total,
                       "method": "censo capturado por clave primaria en una transacción repeatable-read de solo lectura",
                       "period": "mes calendario", "groups": strata_count, "type_proxy": True,
                       "stage_scope": "descriptivo del corte completo; no reconstruye qué dato estaba disponible antes de cada decisión"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "coverage": coverage_counts,
            "index": {"available": False, "meaning": "No se calcula probabilidad ni índice de corrupción; los indicios son anomalías para revisión humana."},
            "priority_analysis": {"policy": "unranked-full-census-v1", "weights_calibrated": False,
                                 "fully_resolved_priorities": 0, "targets": total,
                                 "limitations": ["No existe un conjunto de decisiones judiciales verificadas para calibrar o validar pesos.",
                                                 "Los resultados se ordenan por señal estadística y fecha, no por probabilidad de corrupción."]},
            "source_hash_sha256": digest.hexdigest(),
            "database_generation_consistency_verified": not resume,
            "cohort_generation_note": (f"Conteo exacto de origen y resultados coinciden ({total:,}) dentro de la misma transacción de solo lectura; snapshot PostgreSQL {snapshot}."
                                       if not resume else "Se reanudó desde la captura local completa de 9.249.545 filas. El identificador de la transacción original no quedó guardado tras el error del proceso; no se atribuye verificación de generación entre origen y resultado."),
            "methodology": [
                "Se procesaron todas las filas normalizadas de contratos_procesados, sin modificar PostgreSQL.",
                "La señal de importe atípico compara precio base con Q1 − 1,5×IQR o Q3 + 1,5×IQR; requiere al menos 30 procesos únicos e IQR mayor que cero.",
                "Los pares se agrupan por mes de publicación, tipo de contrato (proxy local de categoría SECOP) y modalidad.",
                "Procesos repetidos o sin identidad oficial única, importes inválidos y grupos insuficientes quedan sin evaluación para esta señal.",
                "La variable observada es precio base total; no se validó contra cantidades ni precios unitarios.",
                "Competencia, ofertas y reiteración histórica quedan como desconocidas porque el corte local no conserva evidencia suficiente para confirmarlas.",
                "Las banderas antiguas de calidad se presentan separadas y no modifican esta señal.",
                "Una anomalía estadística orienta una revisión humana; no prueba sobreprecio, corrupción ni responsabilidad.",
                "No se entrenó un modelo ni se calibraron pesos: faltan expedientes judiciales firmes enlazados con operaciones.",
            ],
        }
        db.executemany("INSERT INTO meta(key,value) VALUES (?,?)", [(k, json_text(v)) for k,v in state.items()])
        db.execute("INSERT INTO meta(key,value) VALUES ('filters',?)", (json_text({
            "contract_types": [x[0] for x in db.execute("SELECT DISTINCT contract_type FROM results WHERE contract_type IS NOT NULL ORDER BY contract_type")],
            "modalities": [x[0] for x in db.execute("SELECT DISTINCT modality FROM results WHERE modality IS NOT NULL ORDER BY modality")],
            "stages": ["ADJUDICACION", "CONVOCATORIA"],
        }),))
        db.execute("INSERT INTO meta(key,value) VALUES ('artifact',?)", (json_text({
            "row_count": total, "source_snapshot": snapshot, "input_sha256": digest.hexdigest(),
            "input_hash_scope": "raw ID, process ID, publication date, type, modality and base amount ordered by primary key",
        }),))
        db.commit()
        db.executescript("DROP TABLE raw; DROP TABLE process_counts; DROP TABLE strata;")
        db.execute("PRAGMA optimize")
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        db.execute("PRAGMA journal_mode=DELETE")
        db.close()
        if conn is not None:
            conn.commit(); conn.close()
        if engine is not None:
            engine.dispose()
        TEMP.replace(TARGET)
        print(json.dumps({"phase": "COMPLETE", "rows": total, "signal": coverage_counts["signal"],
                          "no_evaluable": coverage_counts["no_evaluable_family"],
                          "partial_or_unknown": coverage_counts["partial_or_unknown"],
                          "input_sha256": digest.hexdigest(), "database": str(TARGET),
                          "bytes": TARGET.stat().st_size,
                          "seconds": round(time.monotonic()-started,2)}), flush=True)
    except BaseException:
        db.close()
        if conn is not None:
            conn.rollback(); conn.close()
        if engine is not None:
            engine.dispose()
        raise


if __name__ == "__main__":
    main()
