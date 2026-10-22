"""Diagnose or repair current anomaly rows in resumable PostgreSQL batches."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from core.config import settings  # noqa: E402
from core.database import SessionLocal  # noqa: E402
from modules.ingesta.model.RawSecop import RawSecop  # noqa: E402
from modules.transformacion.model.ContratoAnomaloIncompleto import ContratoAnomaloIncompleto  # noqa: E402
from modules.transformacion.model.ContratoProcesado import ContratoProcesado  # noqa: E402
from modules.transformacion.model.EstadisticaCamposFaltantes import EstadisticaCamposFaltantes  # noqa: E402
from modules.transformacion.repository.transformacion import TransformacionRepository  # noqa: E402
from modules.transformacion.services.normalization_service import detect_anomalies  # noqa: E402


VERSION_REGLAS = "v1.0"
CHECKPOINT_VERSION = 1


def _database_identity() -> dict[str, Any]:
    """Identify a target without persisting credentials in the checkpoint."""
    return {
        "host": settings.DB_HOST,
        "port": settings.DB_PORT,
        "database": settings.DB_NAME,
    }


def _write_checkpoint(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _read_checkpoint(path: Path) -> dict[str, Any]:
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("checkpoint_version") != CHECKPOINT_VERSION:
        raise ValueError("La versión del checkpoint no es compatible")
    if state.get("database") != _database_identity():
        raise ValueError("El checkpoint pertenece a otra base de datos")
    if state.get("version_reglas") != VERSION_REGLAS:
        raise ValueError("La versión de reglas cambió; inicia una reconciliación nueva")
    return state


def _finding_signature(item: Any) -> tuple:
    return (
        item.motivo,
        item.valor_detectado,
        item.tipo_anomalia,
        item.valor_original,
        item.descripcion,
        item.campo_afectado,
    )


def _row_signature(item: ContratoAnomaloIncompleto) -> tuple:
    return (
        item.motivo,
        item.valor_detectado,
        item.tipo_anomalia or item.motivo,
        item.valor_original,
        item.descripcion,
        item.campo_afectado,
    )


def _snapshot(session, max_raw_id: int) -> dict[str, Any]:
    return {
        "contratos_procesados": session.query(ContratoProcesado).filter(
            ContratoProcesado.raw_secop_id <= max_raw_id
        ).count(),
        "anomalias_activas": session.query(ContratoAnomaloIncompleto).filter(
            ContratoAnomaloIncompleto.raw_secop_id <= max_raw_id
        ).count(),
        "estadisticas_campos_faltantes": [
            {
                "campo": row.nombre_campo,
                "contador": row.contador_faltantes,
                "porcentaje": float(row.porcentaje_total or 0),
            }
            for row in session.query(EstadisticaCamposFaltantes).order_by(
                EstadisticaCamposFaltantes.nombre_campo
            ).all()
        ],
    }


def _universe_query(session, *, max_raw_id: int, cutoff: datetime, after_id: int, limit: int):
    return session.query(RawSecop, ContratoProcesado).join(
        ContratoProcesado,
        ContratoProcesado.raw_secop_id == RawSecop.id,
    ).filter(
        RawSecop.id > after_id,
        RawSecop.id <= max_raw_id,
        or_(RawSecop.sincronizado_en.is_(None), RawSecop.sincronizado_en <= cutoff),
    ).order_by(RawSecop.id.asc()).limit(limit).all()


def reconcile(*, apply: bool, batch_size: int, checkpoint_path: Path | None, resume: bool) -> dict[str, Any]:
    if batch_size < 1 or batch_size > 10000:
        raise ValueError("--batch-size debe estar entre 1 y 10000")
    if apply and checkpoint_path is None:
        raise ValueError("--apply requiere --checkpoint para permitir la reanudación")
    if apply and checkpoint_path is not None and checkpoint_path.exists() and not resume:
        raise ValueError("El checkpoint ya existe; usa --resume o elige una ruta nueva")
    if resume and (not apply or checkpoint_path is None or not checkpoint_path.is_file()):
        raise ValueError("--resume requiere --apply y un checkpoint existente")

    session = SessionLocal()
    try:
        started_at = datetime.now(timezone.utc)
        if resume:
            state = _read_checkpoint(checkpoint_path)
            if state.get("status") == "COMPLETED":
                raise ValueError("El checkpoint ya está completo; usa otro archivo para una corrida nueva")
            if state.get("status") not in {"RUNNING", "FAILED"}:
                raise ValueError("El estado del checkpoint no permite reanudar")
            max_raw_id = int(state["universo"]["max_raw_secop_id"])
            cutoff = datetime.fromisoformat(state["universo"]["corte_sincronizacion"])
            after_id = int(state["ultimo_raw_secop_id"])
            started_at = datetime.fromisoformat(state["inicio"])
            before = state["resumen_antes"]
            batch_size = int(state["universo"]["tamano_lote"])
        else:
            max_raw_id = int(session.query(func.max(RawSecop.id)).scalar() or 0)
            cutoff = started_at
            after_id = 0
            before = _snapshot(session, max_raw_id)
            candidates = session.query(func.count(RawSecop.id)).join(
                ContratoProcesado,
                ContratoProcesado.raw_secop_id == RawSecop.id,
            ).filter(
                RawSecop.id <= max_raw_id,
                or_(RawSecop.sincronizado_en.is_(None), RawSecop.sincronizado_en <= cutoff),
            ).scalar() or 0
            state = {
                "checkpoint_version": CHECKPOINT_VERSION,
                "database": _database_identity(),
                "version_reglas": VERSION_REGLAS,
                "inicio": started_at.isoformat(),
                "estado": "DIAGNOSTICO" if not apply else "EN_PROCESO",
                "status": "RUNNING" if apply else "DIAGNOSTIC",
                "ultimo_raw_secop_id": 0,
                "universo": {
                    "max_raw_secop_id": max_raw_id,
                    "corte_sincronizacion": cutoff.isoformat(),
                    "total_candidatos": int(candidates),
                    "tamano_lote": batch_size,
                },
                "resumen_antes": before,
            }
            if apply:
                _write_checkpoint(checkpoint_path, state)

        inspected = int(state.get("evaluados", 0)) if resume else 0
        discrepancies = int(state.get("contratos_con_diferencias", 0)) if resume else 0
        missing = int(state.get("anomalias_faltantes", 0)) if resume else 0
        stale = int(state.get("anomalias_sobrantes_o_distintas", 0)) if resume else 0

        while True:
            rows = _universe_query(
                session,
                max_raw_id=max_raw_id,
                cutoff=cutoff,
                after_id=after_id,
                limit=batch_size,
            )
            if not rows:
                break

            raw_ids = [raw.id for raw, _contract in rows]
            active_rows = session.query(ContratoAnomaloIncompleto).filter(
                ContratoAnomaloIncompleto.raw_secop_id.in_(raw_ids)
            ).all()
            active_by_raw: dict[int, list[ContratoAnomaloIncompleto]] = {}
            for item in active_rows:
                active_by_raw.setdefault(item.raw_secop_id, []).append(item)

            replacements = []
            for raw, contract in rows:
                findings = detect_anomalies(
                    raw.__dict__,
                    raw_secop_id=raw.id,
                    current_date=started_at.date() if isinstance(started_at, datetime) else date.today(),
                )
                expected_by_signature: dict[tuple, int] = {}
                actual_by_signature: dict[tuple, int] = {}
                for finding in findings:
                    signature = _finding_signature(finding)
                    expected_by_signature[signature] = expected_by_signature.get(signature, 0) + 1
                for item in active_by_raw.get(raw.id, []):
                    signature = _row_signature(item)
                    actual_by_signature[signature] = actual_by_signature.get(signature, 0) + 1
                absent_count = sum(
                    max(0, count - actual_by_signature.get(signature, 0))
                    for signature, count in expected_by_signature.items()
                )
                stale_count = sum(
                    max(0, count - expected_by_signature.get(signature, 0))
                    for signature, count in actual_by_signature.items()
                )
                if absent_count or stale_count:
                    discrepancies += 1
                    missing += absent_count
                    stale += stale_count
                    replacements.append((contract.id, raw.id, findings))

            if apply and replacements:
                TransformacionRepository(session).replace_anomalias_batch(replacements)
            inspected += len(rows)
            after_id = int(rows[-1][0].id)
            if apply:
                session.commit()
                state.update({
                    "ultimo_raw_secop_id": after_id,
                    "evaluados": inspected,
                    "contratos_con_diferencias": discrepancies,
                    "anomalias_faltantes": missing,
                    "anomalias_sobrantes_o_distintas": stale,
                    "status": "RUNNING",
                })
                _write_checkpoint(checkpoint_path, state)
            else:
                session.rollback()

        if apply:
            repository = TransformacionRepository(session)
            repository.recalculate_porcentajes_estadisticas_campos()
            session.commit()
        after = _snapshot(session, max_raw_id)
        summary = {
            "modo": "APLICAR" if apply else "DIAGNOSTICO",
            "version_reglas": VERSION_REGLAS,
            "inicio": started_at.isoformat(),
            "fin": datetime.now(timezone.utc).isoformat(),
            "universo": state["universo"],
            "evaluados": inspected,
            "contratos_con_diferencias": discrepancies,
            "anomalias_faltantes": missing,
            "anomalias_sobrantes_o_distintas": stale,
            "resumen_antes": before,
            "resumen_despues": after,
        }
        if apply:
            state.update({
                "status": "COMPLETED",
                "estado": "EXITOSO",
                "fin": summary["fin"],
                "resumen_despues": after,
            })
            _write_checkpoint(checkpoint_path, state)
        return summary
    except Exception as exc:
        session.rollback()
        if apply:
            try:
                TransformacionRepository(session).recalculate_porcentajes_estadisticas_campos()
                session.commit()
            except Exception:
                session.rollback()
        if apply and checkpoint_path is not None and checkpoint_path.exists():
            try:
                failed_state = _read_checkpoint(checkpoint_path)
                failed_state["status"] = "FAILED"
                failed_state["estado"] = "ERROR"
                failed_state["ultimo_error_tipo"] = type(exc).__name__
                _write_checkpoint(checkpoint_path, failed_state)
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        raise
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="aplica las reparaciones; por defecto solo diagnostica")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--checkpoint", type=Path, help="archivo de avance obligatorio con --apply")
    parser.add_argument("--resume", action="store_true", help="reanuda desde un checkpoint fallido o en curso")
    args = parser.parse_args()
    try:
        summary = reconcile(
            apply=args.apply,
            batch_size=args.batch_size,
            checkpoint_path=args.checkpoint,
            resume=args.resume,
        )
    except Exception as exc:
        print(f"Reconciliación fallida: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
