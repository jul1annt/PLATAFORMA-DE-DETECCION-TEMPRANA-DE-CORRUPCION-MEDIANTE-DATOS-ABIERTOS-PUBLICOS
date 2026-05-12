from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from core.database import SessionLocal
from modules.transformacion.dto.request import ContratoProcesadoFilterDTO, ReprocesarRequestDTO
from modules.transformacion.dto.response import ContratoProcesadoResponseDTO, PaginatedResponseDTO
from modules.transformacion.services.trasformacionservice import TransformacionService
from modules.transformacion.repository.transformacion import TransformacionRepository
from datetime import date
from decimal import Decimal
from typing import Optional

router = APIRouter(prefix="/procesados", tags=["Transformacion"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/reprocesar", 
             summary="Reprocesar datos crudos",
             description="Toma registros de la tabla raw_secop que no han sido procesados, los normaliza (fechas, montos, texto) y los guarda en la tabla de contratos procesados.")
def reprocesar_datos(request: ReprocesarRequestDTO, db: Session = Depends(get_db)):
    service = TransformacionService(db)
    try:
        resultado = service.process_raw_data(limite=request.limite, forzar_reproceso=request.forzar_reproceso)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", 
            response_model=PaginatedResponseDTO, 
            summary="Buscar contratos procesados",
            description="Permite realizar búsquedas avanzadas sobre los datos ya normalizados utilizando filtros por entidad, proveedor, fechas y valores.")
def search_procesados(
    entidad: Optional[str] = None,
    proveedor: Optional[str] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    valor_min: Optional[Decimal] = None,
    valor_max: Optional[Decimal] = None,
    tipo_contrato: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    repo = TransformacionRepository(db)
    
    filters = ContratoProcesadoFilterDTO(
        entidad=entidad,
        proveedor=proveedor,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        valor_min=valor_min,
        valor_max=valor_max,
        tipo_contrato=tipo_contrato
    )
    
    skip = (page - 1) * size
    items, total = repo.search(filters=filters, skip=skip, limit=size)
    
    return PaginatedResponseDTO(
        total=total,
        page=page,
        size=size,
        items=items
    )

@router.get("/{id}", response_model=ContratoProcesadoResponseDTO, summary="Obtener detalle de contrato procesado")
def get_procesado(id: int, db: Session = Depends(get_db)):
    repo = TransformacionRepository(db)
    contrato = repo.get_by_id(id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato procesado no encontrado")
    return contrato

@router.get("/", response_model=PaginatedResponseDTO, summary="Listar registros procesados")
def list_procesados(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    # Reuses search with empty filters
    return search_procesados(page=page, size=size, db=db)
