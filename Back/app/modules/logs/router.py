from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.modules.logs.models import LogSincronizacion
from app.modules.logs.schemas import LogSincronizacionResponse

router = APIRouter()

@router.get("/{fuente_id}", response_model=List[LogSincronizacionResponse])
def get_logs_fuente(fuente_id: UUID, db: Session = Depends(get_db)):
    logs = db.query(LogSincronizacion).filter(LogSincronizacion.fuente_id == fuente_id).order_by(LogSincronizacion.fecha.desc()).all()
    return logs
