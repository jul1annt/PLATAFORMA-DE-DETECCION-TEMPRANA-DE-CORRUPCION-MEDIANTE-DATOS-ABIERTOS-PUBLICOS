from datetime import timezone
from modules.ingesta.model import SincronizacionHistorial
from sqlalchemy.orm import Session
from sqlalchemy import func, literal_column, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import Optional
from datetime import datetime
from ..model.FuenteDatos import FuenteDatos
from ..model.RawSecop import RawSecop
from ..model.SincronizacionHistorial import SincronizacionHistorial, EstadoSync
from modules.jobs.model import BackgroundJob
from shared.base_repository import BaseRepository


class IngestaRepository(BaseRepository[FuenteDatos]):
    RAW_INSERT_BATCH_SIZE = 500

    def __init__(self, db: Session):
        super().__init__(FuenteDatos, db)

    def get_by_nombre(self, nombre: str) -> Optional[FuenteDatos]:
        return self.db.query(FuenteDatos).filter(FuenteDatos.nombre == nombre).first()

    def get_activas(self) -> list[FuenteDatos]:
        return self.db.query(FuenteDatos).filter(FuenteDatos.activo == True).all()

    def suspend_source_for_reconciliation(self, fuente_id: int) -> None:
        """Exclude a replaced source from future scheduled synchronizations."""
        self.db.query(FuenteDatos).filter(FuenteDatos.id == fuente_id).update(
            {"activo": False}
        )
        self.db.commit()

    def local_generation_sample(self, fuente_id: int) -> tuple[bool, list[str]]:
        """Sample both ends of the local raw identity without scanning the universe."""
        has_rows = self.db.query(RawSecop.id).filter(RawSecop.fuente_id == fuente_id).first() is not None
        query = self.db.query(RawSecop.socrata_row_id).filter(
            RawSecop.fuente_id == fuente_id,
            RawSecop.socrata_row_id.isnot(None),
            ~RawSecop.socrata_row_id.like("legacy:%"),
        )
        first = query.order_by(RawSecop.id.asc()).limit(6).all()
        last = query.order_by(RawSecop.id.desc()).limit(6).all()
        return has_rows, list(dict.fromkeys(str(row[0]) for row in [*first, *last]))

    def actualizar_ultima_sync(
        self, fuente_id: int, timestamp: datetime, job_id: int | None = None
    ) -> None:
        self.db.query(FuenteDatos).filter(FuenteDatos.id == fuente_id).update(
            {"ultima_sync": timestamp}
        )
        if job_id is not None:
            job = self.db.query(BackgroundJob).filter(BackgroundJob.id == job_id).one()
            result = dict(job.result or {})
            result["checkpoint"] = None
            job.result = result
        self.db.commit()

    def get_sync_checkpoint(
        self, fuente_id: int, current_job_id: int
    ) -> dict | None:
        resource_key = f"ingesta:{fuente_id}"
        current = self.db.query(BackgroundJob).filter(
            BackgroundJob.id == current_job_id,
            BackgroundJob.kind == "INGESTA",
            BackgroundJob.resource_key == resource_key,
        ).first()
        checkpoint = (current.result or {}).get("checkpoint") if current else None
        if checkpoint and checkpoint.get("fuente_id") == fuente_id:
            return dict(checkpoint)
        if current and current.result and "checkpoint" in current.result:
            return None

        previous_jobs = self.db.query(BackgroundJob).filter(
            BackgroundJob.kind == "INGESTA",
            BackgroundJob.resource_key == resource_key,
            BackgroundJob.id < current_job_id,
        ).order_by(BackgroundJob.id.desc()).limit(100).all()
        for previous in previous_jobs:
            previous_result = previous.result or {}
            checkpoint = previous_result.get("checkpoint")
            if checkpoint and checkpoint.get("fuente_id") == fuente_id:
                return dict(checkpoint)
            # A completed job or an explicit null cursor closes its window.
            # An errored job with no result may have failed before persisting
            # its first checkpoint, so continue to the previous resumable job.
            if previous.status == "EXITOSO" or "checkpoint" in previous_result:
                break
        return None

    def guardar_sync_checkpoint(
        self, fuente_id: int, job_id: int, checkpoint: dict
    ) -> None:
        job = self.db.query(BackgroundJob).filter(
            BackgroundJob.id == job_id,
            BackgroundJob.kind == "INGESTA",
            BackgroundJob.resource_key == f"ingesta:{fuente_id}",
        ).one()
        result = dict(job.result or {})
        result["checkpoint"] = checkpoint
        job.result = result
        self.db.commit()

    def clear_sync_checkpoint(self, fuente_id: int, job_id: int) -> None:
        job = self.db.query(BackgroundJob).filter(
            BackgroundJob.id == job_id,
            BackgroundJob.kind == "INGESTA",
            BackgroundJob.resource_key == f"ingesta:{fuente_id}",
        ).one()
        result = dict(job.result or {})
        result["checkpoint"] = None
        job.result = result
        self.db.commit()

    def persistir_lote_y_checkpoint(
        self,
        registros: list[dict],
        fuente_id: int,
        job_id: int,
        checkpoint: dict,
    ) -> int:
        """Commit raw rows and their continuation cursor in one transaction."""
        inserted = self.insertar_raw_secop_bulk(registros, fuente_id)
        job = self.db.query(BackgroundJob).filter(
            BackgroundJob.id == job_id,
            BackgroundJob.kind == "INGESTA",
            BackgroundJob.resource_key == f"ingesta:{fuente_id}",
        ).one()
        result = dict(job.result or {})
        result["checkpoint"] = checkpoint
        job.result = result
        self.db.commit()
        return inserted

    def insertar_raw_secop_bulk(self, registros: list[dict], fuente_id: int) -> int:
        if not registros:
            return 0

        # One process can contain many awards and suppliers. Upsert by Socrata's
        # stable row id, keeping only repeated copies of that exact row within a
        # page. Legacy callers without :id fall back to one synthetic key per
        # process; records without either identifier remain independent rows.
        por_fila: dict[str, tuple[tuple, dict]] = {}
        sin_identificador: list[dict] = []

        def rango_registro(registro: dict) -> tuple:
            updated = registro.get(":updated_at")
            try:
                fecha = datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
                if fecha.tzinfo is None:
                    fecha = fecha.replace(tzinfo=timezone.utc)
                fecha = fecha.astimezone(timezone.utc)
                fecha_rango = fecha.timestamp()
            except (TypeError, ValueError, OverflowError, OSError):
                fecha_rango = float("-inf")
            return (fecha_rango, str(registro.get(":id") or ""))

        for registro in registros:
            row_id = registro.get(":id") or registro.get("socrata_row_id")
            if row_id is None or not str(row_id).strip():
                process_id = str(registro.get("id_del_proceso") or "").strip()
                row_id = f"legacy:{process_id}" if process_id else None
            if row_id is None:
                sin_identificador.append({**registro, "id_del_proceso": None})
                continue
            row_id = str(row_id)
            registro = {**registro, "socrata_row_id": row_id}
            rango = rango_registro(registro)
            existente = por_fila.get(row_id)
            if existente is None or rango > existente[0]:
                por_fila[row_id] = (rango, registro)
        registros = sin_identificador + [item[1] for item in por_fila.values()]

        columnas_validas = {
            c.key
            for c in RawSecop.__table__.columns
            if c.key not in ("id", "sincronizado_en")
        }

        def limpiar_valor(v):
            if isinstance(v, dict):
                return str(v)  # objeto anidado → string
            if isinstance(v, list):
                return str(v)  # array → string
            return v

        limpios = []
        for r in registros:
            fila = {col: limpiar_valor(r.get(col, None)) for col in columnas_validas}
            fila["fuente_id"] = fuente_id
            limpios.append(fila)

        inserted = 0
        for offset in range(0, len(limpios), self.RAW_INSERT_BATCH_SIZE):
            stmt = pg_insert(RawSecop).values(
                limpios[offset : offset + self.RAW_INSERT_BATCH_SIZE]
            )
            excluded = stmt.excluded
            update_columns = {
                col: getattr(excluded, col)
                for col in columnas_validas
                if col not in {"socrata_row_id", "fuente_id"}
            }
            update_columns["fuente_id"] = fuente_id
            update_columns["sincronizado_en"] = func.now()
            stmt = stmt.on_conflict_do_update(
                index_elements=["fuente_id", "socrata_row_id"],
                set_=update_columns,
                where=or_(*(
                    getattr(RawSecop, col).is_distinct_from(getattr(excluded, col))
                    for col in update_columns if col != "sincronizado_en"
                )),
            ).returning(literal_column("(xmax = 0)").label("inserted"))

            result = self.db.execute(stmt)
            inserted += sum(bool(flag) for flag in result.scalars().all())
        return inserted

    def try_sync_lock(self, fuente_id: int) -> bool:
        return bool(self.db.execute(
            text("SELECT pg_try_advisory_lock(:namespace, :fuente_id)"),
            {"namespace": 74201, "fuente_id": fuente_id},
        ).scalar())

    def release_sync_lock(self, fuente_id: int) -> None:
        self.db.execute(
            text("SELECT pg_advisory_unlock(:namespace, :fuente_id)"),
            {"namespace": 74201, "fuente_id": fuente_id},
        )

    def crear_historial(self, fuente_id: int) -> SincronizacionHistorial:
        historial = SincronizacionHistorial(
            fuente_id=fuente_id, estado=EstadoSync.EN_PROCESO
        )
        self.db.add(historial)
        self.db.commit()
        self.db.refresh(historial)
        return historial

    def cerrar_historial(
        self,
        historial_id: int,
        traidos: int,
        insertados: int,
        estado: EstadoSync,
        error: str = None,
    ) -> None:
        self.db.query(SincronizacionHistorial).filter(
            SincronizacionHistorial.id == historial_id
        ).update(
            {
                "fecha_fin": datetime.now(timezone.utc),
                "registros_traidos": traidos,
                "registros_insertados": insertados,
                "registros_duplicados": traidos - insertados,
                "estado": estado,
                "mensaje_error": error,
            }
        )
        self.db.commit()

    def count_historial(self, fuente_id: int | None = None) -> int:
        query = self.db.query(SincronizacionHistorial)
        if fuente_id is not None:
            query = query.filter(SincronizacionHistorial.fuente_id == fuente_id)
        return query.count()

    def resumen_historial(self) -> dict[str, int]:
        resumen = {"total": 0, "exitoso": 0, "en_proceso": 0, "error": 0, "parcial": 0}
        estados = {
            EstadoSync.EXITOSO: "exitoso",
            EstadoSync.EN_PROCESO: "en_proceso",
            EstadoSync.ERROR: "error",
            EstadoSync.PARCIAL: "parcial",
        }
        rows = self.db.query(
            SincronizacionHistorial.estado,
            func.count(SincronizacionHistorial.id),
        ).group_by(SincronizacionHistorial.estado).all()
        for estado, cantidad in rows:
            resumen[estados[estado]] = int(cantidad)
            resumen["total"] += int(cantidad)
        return resumen

    def get_historial(
        self,
        fuente_id: int = None,
        limit: int | None = None,
        skip: int = 0,
    ) -> list[SincronizacionHistorial]:
        query = self.db.query(SincronizacionHistorial)
        if fuente_id:
            query = query.filter(SincronizacionHistorial.fuente_id == fuente_id)
        query = query.order_by(SincronizacionHistorial.fecha_inicio.desc(), SincronizacionHistorial.id.desc())
        if skip:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def get_historial_pagina(
        self,
        skip: int,
        limit: int,
        fuente_id: int | None = None,
    ) -> tuple[list[tuple[SincronizacionHistorial, str | None]], int]:
        query = self.db.query(SincronizacionHistorial, FuenteDatos.nombre).outerjoin(
            FuenteDatos, FuenteDatos.id == SincronizacionHistorial.fuente_id
        )
        if fuente_id is not None:
            query = query.filter(SincronizacionHistorial.fuente_id == fuente_id)
        rows = query.order_by(
            SincronizacionHistorial.fecha_inicio.desc(), SincronizacionHistorial.id.desc()
        ).offset(skip).limit(limit).all()
        return rows, self.count_historial(fuente_id)

    def get_comparativa_fuentes(self) -> list[dict]:
        summary = (
            select(
                SincronizacionHistorial.fuente_id.label("fuente_id"),
                func.coalesce(func.sum(SincronizacionHistorial.registros_traidos), 0).label("traidos"),
                func.coalesce(func.sum(SincronizacionHistorial.registros_insertados), 0).label("insertados"),
                func.coalesce(func.sum(SincronizacionHistorial.registros_duplicados), 0).label("duplicados"),
            )
            .group_by(SincronizacionHistorial.fuente_id)
            .subquery()
        )
        latest = (
            select(
                SincronizacionHistorial.fuente_id.label("fuente_id"),
                SincronizacionHistorial.estado.label("estado"),
                SincronizacionHistorial.mensaje_error.label("mensaje_error"),
                func.row_number().over(
                    partition_by=SincronizacionHistorial.fuente_id,
                    order_by=(SincronizacionHistorial.fecha_inicio.desc(), SincronizacionHistorial.id.desc()),
                ).label("rank"),
            )
            .subquery()
        )
        rows = self.db.execute(
            select(FuenteDatos, summary.c.traidos, summary.c.insertados,
                   summary.c.duplicados, latest.c.estado, latest.c.mensaje_error)
            .outerjoin(summary, summary.c.fuente_id == FuenteDatos.id)
            .outerjoin(latest, (latest.c.fuente_id == FuenteDatos.id) & (latest.c.rank == 1))
            .order_by(FuenteDatos.nombre)
        ).all()
        result = []
        for fuente, traidos, insertados, duplicados, estado, mensaje_error in rows:
            total_traidos = int(traidos or 0)
            total_insertados = int(insertados or 0)
            total_duplicados = int(duplicados or 0)
            result.append({
                "fuente_id": fuente.id,
                "nombre": fuente.nombre,
                "endpoint": fuente.endpoint,
                "ultima_sync_estado": estado,
                "ultima_sync_error": mensaje_error,
                "total_traidos": total_traidos,
                "total_insertados": total_insertados,
                "total_duplicados": total_duplicados,
                "tasa_duplicidad": round(total_duplicados / total_traidos * 100, 2) if total_traidos else 0.0,
            })
        return result
