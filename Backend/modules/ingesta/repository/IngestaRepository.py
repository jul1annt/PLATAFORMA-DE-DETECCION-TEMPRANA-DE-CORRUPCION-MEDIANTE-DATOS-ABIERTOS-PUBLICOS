from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import Optional
from datetime import datetime
from ..model.FuenteDatos import FuenteDatos
from ..model.RawSecop import RawSecop
from shared.base_repository import BaseRepository

class IngestaRepository(BaseRepository[FuenteDatos]):

    def __init__(self, db: Session):
        super().__init__(FuenteDatos, db)

    def get_by_nombre(self, nombre: str) -> Optional[FuenteDatos]:
        return self.db.query(FuenteDatos).filter(FuenteDatos.nombre == nombre).first()

    def get_activas(self) -> list[FuenteDatos]:
        return self.db.query(FuenteDatos).filter(FuenteDatos.activo == True).all()

    def actualizar_ultima_sync(self, fuente_id: int, timestamp: datetime) -> None:
        self.db.query(FuenteDatos)\
            .filter(FuenteDatos.id == fuente_id)\
            .update({"ultima_sync": timestamp})
        self.db.commit()

    def insertar_raw_secop_bulk(self, registros: list[dict], fuente_id: int) -> int:
        if not registros:
            return 0

        for r in registros:
            r["fuente_id"] = fuente_id

        # INSERT ... ON CONFLICT DO NOTHING (evita duplicados por id_del_proceso)
        stmt = pg_insert(RawSecop).values(registros)
        stmt = stmt.on_conflict_do_nothing(index_elements=["id_del_proceso"])

        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount