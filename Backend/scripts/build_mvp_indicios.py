"""Build an explainable, read-only risk-indicator snapshot from the local API.

The source and original publication remain untouched. The snapshot describes a
complete published cohort and never presents a statistical anomaly as proof of
corruption.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import urllib.parse
from urllib.parse import urlparse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.motor_riesgo.baseline_coverage import baseline_coverage
from modules.motor_riesgo.robust_priority import assess as assess_priority
from modules.motor_riesgo.rules import iqr_finding_from_reference, iqr_reference

API = "http://127.0.0.1:8000/api/procesados/search"
COHORT_START = date(2026, 9, 25)
COHORT_END = date(2026, 9, 30)
SNAPSHOT_CUT = "2026-10-01"
MAX_ROWS = 25_000
OUT = Path(__file__).resolve().parents[1] / ".codex-analytics-postgres" / "mvp-risk-20261020"


def fetch(offset: int, limit: int = 1000) -> dict:
    params = urllib.parse.urlencode({"fecha_inicio": COHORT_START.isoformat(), "fecha_fin": COHORT_END.isoformat(),
                                     "limit": limit, "offset": offset, "sort": "id", "order": "asc"})
    request = urllib.request.Request(API + "?" + params, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError("La API pública local no respondió correctamente")
        return json.load(response)


def safe_source_url(value):
    if isinstance(value, dict):
        value = value.get("url")
    if not isinstance(value, str) or len(value) > 4096:
        return None
    try:
        parsed = urlparse(value.strip())
        port = parsed.port
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or not any(host == d or host.endswith("." + d) for d in ("secop.gov.co", "contratos.gov.co"))
            or parsed.username or parsed.password or port not in (None, 443)
            or "login" in parsed.path.lower()):
        return None
    return value.strip()


def canonical_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str,
                                     separators=(",", ":")).encode()).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    first = fetch(0)
    total = first.get("total")
    if type(total) is not int or total < 1 or total > MAX_ROWS or len(first.get("items", [])) != min(1000, total):
        raise RuntimeError("La cohorte no cumple el límite o la paginación verificable")
    rows = list(first["items"])
    for offset in range(1000, total, 1000):
        page = fetch(offset)
        expected = min(1000, total - offset)
        if (page.get("total") != total or page.get("page") != offset // 1000 + 1
                or len(page.get("items", [])) != expected):
            raise RuntimeError("La cohorte cambió durante la lectura; no se publica una captura parcial")
        rows.extend(page["items"])
    if len(rows) != total or len({r.get("id") for r in rows}) != total:
        raise RuntimeError("La descarga no cubre filas únicas de la cohorte")

    # Official SECOP category is absent from the local public read model. Use
    # contract type only as an explicit proxy, with calendar-month strata.
    groups: dict[tuple, list] = defaultdict(list)
    process_counts = Counter(str(r.get("id_del_proceso") or "").strip() for r in rows)
    for row in rows:
        published = str(row.get("fecha_publicacion_normalizada") or "")
        period = published[:7] if len(published) >= 7 else ""
        groups[(period, row.get("tipo_contrato_normalizado") or "", row.get("modalidad_contratacion") or "")].append(row)

    results = []
    for (period, contract_type, modality), members in groups.items():
        usable = []
        for row in members:
            process = str(row.get("id_del_proceso") or "").strip()
            amount = row.get("precio_base_normalizado")
            if process and process_counts[process] == 1 and amount is not None:
                try:
                    if Decimal(str(amount)) > 0:
                        usable.append(row)
                except Exception:
                    pass
        amounts = [row["precio_base_normalizado"] for row in usable]
        reference = iqr_reference(amounts)
        for row in members:
            process = str(row.get("id_del_proceso") or "").strip()
            finding = iqr_finding_from_reference(row.get("precio_base_normalizado"), reference)
            if not process or process_counts[process] > 1:
                finding.update(detected=None, reason="identidad_de_proceso_ambigua")

            # SECOP evidence in this snapshot does not contain a complete
            # adjudication history or verified bidders; the coverage policy
            # preserves those indicators as unknown rather than zero.
            stage = "ADJUDICACION" if row.get("fecha_adjudicacion_normalizada") else "CONVOCATORIA"
            coverage = baseline_coverage(
                {"modalidad": modality, "oferentes": None, "directas_90d": None, "reiteraciones_30d": None},
                stage, finding,
            )
            missing = [
                f"{name}:{indicator.get('reason') or 'evidencia_insuficiente'}"
                for name, indicator in coverage["indicators"].items()
                if indicator["status"] == "NO_EVALUABLE"
            ]
            has_signal = coverage["confirmed_signal_count"] > 0
            if has_signal:
                status = "CON_SENAL_CONFIRMADA"
            elif coverage["evaluated_families"] == 0:
                status = "NO_EVALUABLE"
            elif coverage["unevaluable_families"]:
                status = "EVIDENCIA_INSUFICIENTE"
            else:
                status = "SIN_SENAL_OBSERVADA"

            results.append({
                "id": row.get("id"), "raw_secop_id": row.get("raw_secop_id"),
                "process_id": process or None, "entity": row.get("entidad_normalizada"),
                "supplier": row.get("proveedor_normalizado"), "published_at": row.get("fecha_publicacion_normalizada"),
                "contract_type": contract_type or None, "modality": modality or None,
                "amount": row.get("precio_base_normalizado"), "award_amount": row.get("valor_total_normalizado"),
                "stage": stage, "comparison_period": period or None,
                "source_url": safe_source_url(row.get("urlproceso")),
                "signal": has_signal, "status": status, "coverage": coverage,
                "missing_evidence": missing,
                "evidence": {k: str(v) if isinstance(v, Decimal) else v for k, v in finding.items()},
                "legacy_data_quality_flag": bool(row.get("es_sospechoso")),
            })

    source_hash = canonical_hash(rows)
    priority_input = {
        "policy": "current-cut-joint-families-v1",
        "temporal_scope": "current_cut_descriptive_not_stage_prediction",
        "snapshot_cut": SNAPSHOT_CUT,
        "cohort_canonical_sha256": source_hash,
        "targets": len(results), "training_eligible": False, "publication_authorized": False,
        "database_generation_consistency_verified": False,
        "results": [{"contract_id": int(row["raw_secop_id"]), "snapshot_cut": SNAPSHOT_CUT,
                     "publication_authorized": False, "training_eligible": False,
                     "coverage": row["coverage"]} for row in results],
    }
    priority = assess_priority(priority_input)
    priority_by_id = {item["contract_id"]: item for item in priority["results"]}
    for row in results:
        assessment = priority_by_id[int(row["raw_secop_id"])]
        row["priority"] = {key: assessment[key] for key in (
            "best_rank_bound", "worst_rank_bound", "comparison_population", "priority_is_fully_resolved", "review_route")}
        coverage = row["coverage"]
        row["coverage"] = {
            "evaluated_families": coverage["evaluated_families"],
            "applicable_families": coverage["applicable_families"],
            "unevaluable_families": coverage["unevaluable_families"],
            "complete_score": coverage["complete_score"],
            "score_interval": coverage["score_interval"],
            "families": {name: item["status"] for name, item in coverage["families"].items()},
            "indicators": {name: {"status": item["status"], "reason": item["reason"]}
                           for name, item in coverage["indicators"].items()},
        }

    # Signals are shown first for navigation, but there is no fabricated total
    # ranking when family evidence is incomplete.
    results.sort(key=lambda item: (not item["signal"], str(item.get("published_at") or ""),
                                   str(item.get("process_id") or "")))
    coverage_counts = {
        "signal": sum(bool(row["signal"]) for row in results),
        "no_confirmed_signal": sum(not row["signal"] for row in results),
        "no_evaluable_family": sum(row["status"] == "NO_EVALUABLE" for row in results),
        "partial_or_unknown": sum(row["coverage"]["unevaluable_families"] > 0 for row in results),
        "complete_family_evaluation": sum(row["coverage"]["complete_score"] is not None for row in results),
        "by_stage": {stage: sum(row["stage"] == stage for row in results)
                     for stage in ("CONVOCATORIA", "ADJUDICACION")},
    }
    state = {
        "name": "Motor local de señales de riesgo explicables",
        "status": "MVP_RULES_ONLY", "snapshot_cut": SNAPSHOT_CUT,
        "cohort": {"start": COHORT_START.isoformat(), "end": COHORT_END.isoformat(), "rows": total,
                   "method": "cohorte completa de seis días consultada con paginación verificada",
                   "period": "mes calendario", "groups": len(groups), "type_proxy": True,
                   "stage_scope": "descriptivo del corte actual; no reconstruye el conocimiento histórico de cada etapa"},
        "database_generation_consistency_verified": False,
        "cohort_generation_note": "El API permitió verificar paginación, total estable e IDs únicos; no expone una revisión común de generación para probar que todas las páginas pertenezcan a la misma transacción.",
        "created_at": datetime.now(timezone.utc).isoformat(), "source_hash_sha256": source_hash,
        "coverage": coverage_counts,
        "priority_analysis": {key: value for key, value in priority.items() if key != "results"},
        "index": {"available": False,
                  "meaning": "No se calcula un índice 0–100 ni una probabilidad; se publican familias confirmadas, cobertura y límites de prioridad."},
        "methodology": [
            "Señal de importe atípico: presupuesto base fuera de Q1 − 1,5×IQR o Q3 + 1,5×IQR, con mínimo 30 operaciones comparables e IQR positivo.",
            "Comparación por mes, tipo de contrato disponible como proxy y modalidad. El código oficial de categoría SECOP no está expuesto en esta lectura.",
            "Procesos repetidos en la cohorte no se usan como pares independientes. Es una descripción del corte actual, no una reconstrucción de la información conocida en cada etapa.",
            "Competencia, reiteración y contratación directa requieren ofertas verificadas e historia completa. Se conservan como no evaluables cuando esos insumos faltan; las respuestas SECOP no se tratan como oferentes.",
            "La prioridad v8 usa pesos iguales de referencia por familia y límites por cobertura. No es una escala calibrada y no ordena cuando la evidencia no permite comparar.",
            "La paginación mantuvo total e IDs únicos, pero la API no ofrece una marca transaccional común; no se certifica una generación consistente entre páginas.",
            "Una señal estadística orienta una revisión; no prueba sobreprecio, corrupción ni responsabilidad. No hay modelos judiciales entrenados ni aprobados.",
            "La bandera histórica de calidad se muestra por separado y no participa en la evaluación de riesgo.",
            f"Cohorte completa del {COHORT_START.isoformat()} al {COHORT_END.isoformat()}, bajo el corte publicado {SNAPSHOT_CUT}. No extrapolar a otros periodos, sectores o etapas.",
        ],
        "results": results,
    }
    target = OUT / "snapshot-v8.json"
    temp = OUT / "snapshot-v8.json.tmp"
    if target.exists():
        raise RuntimeError("El snapshot v5 ya existe: conservarlo y crear una nueva versión")
    temp.write_text(json.dumps(state, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    temp.replace(target)
    print(json.dumps({"cohort_rows": total, "groups": len(groups), **coverage_counts,
                      "sha256": source_hash, "file_bytes": target.stat().st_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
