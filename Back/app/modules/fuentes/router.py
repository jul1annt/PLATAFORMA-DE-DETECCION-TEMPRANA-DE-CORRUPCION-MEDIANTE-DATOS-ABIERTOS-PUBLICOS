from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.modules.fuentes.models import FuenteDatos
from app.modules.fuentes.schemas import FuenteDatosCreate, FuenteDatosUpdate, FuenteDatosResponse

router = APIRouter()

@router.post("/", response_model=FuenteDatosResponse)
def create_fuente(fuente_in: FuenteDatosCreate, db: Session = Depends(get_db)):
    fuente = FuenteDatos(**fuente_in.model_dump())
    db.add(fuente)
    db.commit()
    db.refresh(fuente)
    return fuente

@router.get("/", response_model=List[FuenteDatosResponse])
def read_fuentes(db: Session = Depends(get_db)):
    fuentes = db.query(FuenteDatos).all()
    return fuentes

@router.put("/{id}", response_model=FuenteDatosResponse)
def update_fuente(id: UUID, fuente_in: FuenteDatosUpdate, db: Session = Depends(get_db)):
    fuente = db.query(FuenteDatos).filter(FuenteDatos.id == id).first()
    if not fuente:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    
    update_data = fuente_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(fuente, key, value)
        
    db.commit()
    db.refresh(fuente)
    return fuente

@router.patch("/{id}/activar", response_model=FuenteDatosResponse)
def activate_fuente(id: UUID, db: Session = Depends(get_db)):
    fuente = db.query(FuenteDatos).filter(FuenteDatos.id == id).first()
    if not fuente:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    fuente.estado = "activa"
    db.commit()
    db.refresh(fuente)
    return fuente

@router.patch("/{id}/desactivar", response_model=FuenteDatosResponse)
def deactivate_fuente(id: UUID, db: Session = Depends(get_db)):
    fuente = db.query(FuenteDatos).filter(FuenteDatos.id == id).first()
    if not fuente:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    fuente.estado = "inactiva"
    db.commit()
    db.refresh(fuente)
    return fuente
