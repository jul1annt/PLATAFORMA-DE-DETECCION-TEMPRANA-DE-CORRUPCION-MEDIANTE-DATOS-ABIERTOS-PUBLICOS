"""Finalize metadata for the already-computed, isolated full-volume MVP."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.config import settings


DB_PATH = ROOT / ".codex-analytics-postgres" / "mvp-risk-20261020" / "full-volume-v3.sqlite"
REPORT_EVERY = 500_000


def json_text(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str, allow_nan=False)


def main() -> None:
    if not DB_PATH.is_file():
        raise SystemExit(f"No existe el artefacto publicado: {DB_PATH}")

    started = time.monotonic()
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    signal_counts = dict(conn.execute("""
        SELECT signal,COUNT(*) FROM results INDEXED BY ix_results_public_order
         GROUP BY signal
    """))
    status_stage_counts = list(conn.execute("""
        SELECT status,stage,COUNT(*) FROM results INDEXED BY ix_results_status_stage
         GROUP BY status,stage
    """))
    total = sum(signal_counts.values())
    signal_count = signal_counts.get(1, 0)
    status_counts = {}
    stage_counts = {}
    for status, stage, count in status_stage_counts:
        status_counts[status] = status_counts.get(status, 0) + count
        stage_counts[stage] = stage_counts.get(stage, 0) + count
    no_eval = status_counts.get("NO_EVALUABLE", 0)
    partial = status_counts.get("EVIDENCIA_INSUFICIENTE", 0)
    complete = status_counts.get("CON_SENAL_CONFIRMADA", 0) + status_counts.get("SIN_SENAL_OBSERVADA", 0)
    # The requested dashboard summary does not need a second full index sweep
    # solely to derive date extrema. Keep those fields explicitly unknown.
    minimum = maximum = None
    stats = {
        "total": total,
        "signal": signal_count,
        "no_confirmed_signal": total - signal_count,
        "no_evaluable_family": no_eval,
        "partial_or_unknown": partial,
        "complete_family_evaluation": complete,
        "by_stage": stage_counts,
    }

    if stats["total"] != 9_249_545:
        raise RuntimeError(f"El corte no tiene las 9.249.545 filas esperadas: {stats['total']:,}")
    buckets = (stats["signal"] + stats["complete_family_evaluation"] - stats["signal"]
               + stats["partial_or_unknown"] + stats["no_evaluable_family"])
    if buckets != stats["total"]:
        raise RuntimeError(f"La distribución de estados no suma el total: {buckets:,} != {stats['total']:,}")

    groups = conn.execute("SELECT COUNT(*) FROM strata").fetchone()[0]
    filters = {
        "contract_types": [r[0] for r in conn.execute(
            "SELECT DISTINCT contract_type FROM strata WHERE contract_type IS NOT NULL ORDER BY contract_type")],
        "modalities": [r[0] for r in conn.execute(
            "SELECT DISTINCT modality FROM strata WHERE modality IS NOT NULL ORDER BY modality")],
        "stages": ["ADJUDICACION", "CONVOCATORIA"],
    }
    state = {
        "name": "Motor local de señales de riesgo explicables",
        "status": "MVP_RULES_ONLY",
        "snapshot_cut": settings.RISK_BASELINE_CUT_DATE.isoformat(),
        "cohort": {"start": minimum, "end": maximum, "rows": stats["total"],
                   "method": "censo capturado por clave primaria en una transacción repeatable-read de solo lectura",
                   "period": "mes calendario", "groups": groups, "type_proxy": True,
                   "stage_scope": "descriptivo del corte completo; no reconstruye qué dato estaba disponible antes de cada decisión"},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "coverage": stats,
        "index": {"available": False, "meaning": "No se calcula probabilidad ni índice de corrupción; los indicios son anomalías para revisión humana."},
        "priority_analysis": {"policy": "unranked-full-census-v1", "weights_calibrated": False,
                              "fully_resolved_priorities": 0, "targets": stats["total"],
                              "limitations": ["No existe un conjunto de decisiones judiciales verificadas para calibrar o validar pesos.",
                                              "Los resultados se ordenan por señal estadística y fecha, no por probabilidad de corrupción."]},
        "source_hash_sha256": None,
        "database_generation_consistency_verified": False,
        "cohort_generation_note": "Se reanudó desde la captura local completa de 9.249.545 filas. El identificador de la transacción PostgreSQL original no quedó retenido al interrumpirse el proceso; no se atribuye verificación de generación entre origen y resultado.",
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
    artifact = {"row_count": stats["total"], "source_snapshot": "reanudado desde captura local completa",
                "input_sha256": None,
                "input_hash_scope": "no recalculado durante la publicación resumida"}
    conn.executemany("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)",
                     [(key, json_text(value)) for key, value in state.items()])
    conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('filters',?)", (json_text(filters),))
    conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('artifact',?)", (json_text(artifact),))
    conn.commit()
    # This artifact includes a 38 GB WAL. A deep full-database scan here can
    # block local publication for a long time; metadata is committed first
    # and the endpoint performs targeted reads against the published rows.
    check = "not_run_large_wal"
    conn.close()

    print(json.dumps({"phase": "COMPLETE", "rows": stats["total"],
                      "coverage": stats, "groups": groups, "quick_check": check,
                      "input_sha256": None, "database": str(DB_PATH),
                      "bytes": DB_PATH.stat().st_size,
                      "seconds": round(time.monotonic() - started, 2)}), flush=True)


if __name__ == "__main__":
    main()
