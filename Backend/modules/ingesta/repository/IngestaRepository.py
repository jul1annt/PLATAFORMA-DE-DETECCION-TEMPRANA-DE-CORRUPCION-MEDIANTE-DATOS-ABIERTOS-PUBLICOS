from datetime import timezone
from modules.ingesta.model import SincronizacionHistorial
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import Optional
from datetime import datetime
from ..model.FuenteDatos import FuenteDatos
from ..model.RawSecop import RawSecop
from ..model.SincronizacionHistorial import SincronizacionHistorial, EstadoSync
from shared.base_repository import BaseRepository


class IngestaRepository(BaseRepository[FuenteDatos]):
    def __init__(self, db: Session):
        super().__init__(FuenteDatos, db)

    def get_by_nombre(self, nombre: str) -> Optional[FuenteDatos]:
        return self.db.query(FuenteDatos).filter(FuenteDatos.nombre == nombre).first()

    def get_activas(self) -> list[FuenteDatos]:
        return self.db.query(FuenteDatos).filter(FuenteDatos.activo == True).all()

    def actualizar_ultima_sync(self, fuente_id: int, timestamp: datetime) -> None:
        self.db.query(FuenteDatos).filter(FuenteDatos.id == fuente_id).update(
            {"ultima_sync": timestamp}
        )
        self.db.commit()

    def insertar_raw_secop_bulk(self, registros: list[dict], fuente_id: int) -> int:
        if not registros:
            return 0

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

        stmt = pg_insert(RawSecop).values(limpios)
        stmt = stmt.on_conflict_do_nothing(index_elements=["id_del_proceso"])

        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount

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

    def get_historial(self, fuente_id: int = None) -> list[SincronizacionHistorial]:
        query = self.db.query(SincronizacionHistorial)
        if fuente_id:
            query = query.filter(SincronizacionHistorial.fuente_id == fuente_id)
        return query.order_by(SincronizacionHistorial.fecha_inicio.desc()).all()