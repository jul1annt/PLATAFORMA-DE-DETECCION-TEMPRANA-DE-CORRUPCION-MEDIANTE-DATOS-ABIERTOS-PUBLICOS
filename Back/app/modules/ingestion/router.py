from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.modules.fuentes.models import FuenteDatos
from app.modules.logs.schemas import LogSincronizacionResponse
from app.modules.ingestion.service import run_ingestion_for_source

router = APIRouter()

@router.post("/{fuente_id}", response_model=LogSincronizacionResponse)
def sync_fuente_manual(fuente_id: UUID, db: Session = Depends(get_db)):
    fuente = db.query(FuenteDatos).filter(FuenteDatos.id == fuente_id).first()
    if not fuente:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    if fuente.estado != "activa":
        raise HTTPException(status_code=400, detail="La fuente debe estar activa para sincronizar")
    
    log = run_ingestion_for_source(db, fuente)
    return log
