from modules.ingesta.dto.response import SincronizacionHistorialResponseDTO
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from core.dependencies import get_db
from ..services.IngestaService import IngestaService
from ..dto.request import FuenteDatosCreateDTO, FuenteDatosUpdateDTO
from ..dto.response import FuenteDatosResponseDTO, ConexionTestResponseDTO
from typing import Optional

router = APIRouter(prefix="/ingesta/fuentes", tags=["Ingesta - Fuentes de Datos"])

def get_service(db: Session = Depends(get_db)) -> IngestaService:
    return IngestaService(db)

@router.post("/", response_model=FuenteDatosResponseDTO, status_code=status.HTTP_201_CREATED)
def crear_fuente(dto: FuenteDatosCreateDTO, svc: IngestaService = Depends(get_service)):
    return svc.crear_fuente(dto)

@router.get("/", response_model=list[FuenteDatosResponseDTO])
def listar_fuentes(svc: IngestaService = Depends(get_service)):
    return svc.listar_fuentes()

# ── Rutas estáticas primero ────────────────────────────────────────────

@router.get("/sincronizaciones", response_model=list[SincronizacionHistorialResponseDTO])
def listar_historial(svc: IngestaService = Depends(get_service)):
    return svc.listar_historial()

# ── Rutas dinámicas después ────────────────────────────────────────────

@router.get("/{fuente_id}", response_model=FuenteDatosResponseDTO)
def obtener_fuente(fuente_id: int, svc: IngestaService = Depends(get_service)):
    return svc.obtener_fuente(fuente_id)

@router.put("/{fuente_id}", response_model=FuenteDatosResponseDTO)
def actualizar_fuente(fuente_id: int, dto: FuenteDatosUpdateDTO, svc: IngestaService = Depends(get_service)):
    return svc.actualizar_fuente(fuente_id, dto)

@router.delete("/{fuente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_fuente(fuente_id: int, svc: IngestaService = Depends(get_service)):
    return svc.eliminar_fuente(fuente_id)

@router.post("/{fuente_id}/probar", response_model=ConexionTestResponseDTO)
def probar_conexion(fuente_id: int, svc: IngestaService = Depends(get_service)):
    return svc.probar_conexion(fuente_id)

@router.post("/{fuente_id}/sincronizar")
def sincronizar_fuente(fuente_id: int, svc: IngestaService = Depends(get_service)):
    return svc.sincronizar_fuente(fuente_id)

@router.get("/{fuente_id}/sincronizaciones", response_model=list[SincronizacionHistorialResponseDTO])
def historial_por_fuente(fuente_id: int, svc: IngestaService = Depends(get_service)):
    return svc.listar_historial(fuente_id=fuente_id)