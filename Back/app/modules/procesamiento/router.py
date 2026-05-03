from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.modules.procesamiento.models import ContratoProcesado, ResumenCalidad, CalidadDatos, CambiosContratos
from app.modules.procesamiento.schemas import (
    ProcessResponse,
    ContratoProcesadoResponse,
    ResumenCalidadResponse,
    CalidadDatosResponse,
    CambiosContratosResponse
)
from app.modules.procesamiento.services.processor import process_data_pipeline

router = APIRouter()

@router.post("/process", response_model=ProcessResponse, summary="Ejecuta el pipeline de procesamiento")
def process_data(db: Session = Depends(get_db)):
    """
    Ejecuta el pipeline de procesamiento de datos crudos:
    1. Lee de datos_crudos
    2. Normaliza datos
    3. Detecta duplicados (hash)
    4. Valida calidad (incompletos, sospechosos)
    5. Detecta cambios en contratos existentes
    6. Guarda en contratos_procesados y tablas relacionadas
    """
    try:
        result = process_data_pipeline(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el procesamiento: {str(e)}")

@router.get("/contratos", response_model=List[ContratoProcesadoResponse], summary="Obtener contratos procesados")
def get_contratos(
    estado: Optional[str] = Query(None, description="Filtrar por estado de calidad (OK, INCOMPLETO, SOSPECHOSO)"),
    db: Session = Depends(get_db)
):
    """
    Devuelve la lista de contratos procesados. Permite filtrar por estado_calidad.
    """
    query = db.query(ContratoProcesado)
    if estado:
        query = query.filter(ContratoProcesado.estado_calidad == estado.upper())
    return query.all()

@router.get("/calidad/resumen", response_model=List[ResumenCalidadResponse], summary="Resumen de calidad de datos")
def get_calidad_resumen(db: Session = Depends(get_db)):
    """
    Devuelve el resumen de calidad agrupado por fuente de datos y ejecución.
    """
    return db.query(ResumenCalidad).order_by(ResumenCalidad.fecha.desc()).all()

@router.get("/calidad/problemas", response_model=List[CalidadDatosResponse], summary="Problemas de calidad detectados")
def get_calidad_problemas(db: Session = Depends(get_db)):
    """
    Devuelve el registro detallado de los problemas de calidad encontrados (INCOMPLETO, SOSPECHOSO).
    """
    return db.query(CalidadDatos).order_by(CalidadDatos.fecha.desc()).all()

@router.get("/cambios", response_model=List[CambiosContratosResponse], summary="Historial de cambios en contratos")
def get_cambios(db: Session = Depends(get_db)):
    """
    Devuelve el historial de cambios detectados en contratos previamente procesados.
    """
    return db.query(CambiosContratos).order_by(CambiosContratos.fecha.desc()).all()
