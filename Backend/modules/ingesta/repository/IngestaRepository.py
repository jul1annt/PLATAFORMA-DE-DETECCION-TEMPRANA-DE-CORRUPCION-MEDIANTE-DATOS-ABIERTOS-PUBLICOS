import datetime
from sqlalchemy.orm import Session
from typing import Optional
from ..model.FuenteDatos import FuenteDatos
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