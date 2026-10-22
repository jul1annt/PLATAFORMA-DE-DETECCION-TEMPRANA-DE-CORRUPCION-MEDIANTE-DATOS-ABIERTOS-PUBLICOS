from modules.ingesta.dto.response import (
    ComparativaFuenteDTO,
    SincronizacionHistorialResponseDTO,
    SincronizacionHistorialPaginaDTO,
    SincronizacionHistorialResumenDTO,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from core.database import get_db
from ..services.IngestaService import IngestaService
from ..dto.request import FuenteDatosCreateDTO, FuenteDatosUpdateDTO
from ..dto.response import FuenteDatosResponseDTO, ConexionTestResponseDTO
from typing import Optional
from gateway.middlewares.auth_middleware import get_current_admin
from shared.exporting import render_export
from ..repository.IngestaRepository import IngestaRepository
from modules.jobs.dto import BackgroundJobAccepted
from modules.jobs.service import enqueue_job, to_job_accepted
from shared.request_validation import reject_unknown_query_params

router = APIRouter(
    prefix="/ingesta/fuentes",
    tags=["Ingesta - Fuentes de Datos"],
    dependencies=[Depends(get_current_admin)],
)

def get_service(db: Session = Depends(get_db)) -> IngestaService:
    return IngestaService(db)

@router.post("/", response_model=FuenteDatosResponseDTO, status_code=status.HTTP_201_CREATED)
def crear_fuente(dto: FuenteDatosCreateDTO, svc: IngestaService = Depends(get_service)):
    return svc.crear_fuente(dto)

@router.get("/", response_model=list[FuenteDatosResponseDTO])
def listar_fuentes(request: Request, svc: IngestaService = Depends(get_service)):
    reject_unknown_query_params(request, set())
    return svc.listar_fuentes()

# ── Rutas estáticas primero ────────────────────────────────────────────

@router.get("/sincronizaciones", response_model=list[SincronizacionHistorialResponseDTO])
def listar_historial(request: Request, svc: IngestaService = Depends(get_service)):
    reject_unknown_query_params(request, set())
    return svc.listar_historial()

@router.get("/sincronizaciones/resumen", response_model=SincronizacionHistorialResumenDTO)
def resumen_historial(request: Request, svc: IngestaService = Depends(get_service)):
    reject_unknown_query_params(request, set())
    return svc.resumen_historial()

@router.get("/sincronizaciones/pagina", response_model=SincronizacionHistorialPaginaDTO)
def listar_historial_pagina(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    svc: IngestaService = Depends(get_service),
):
    reject_unknown_query_params(request, {"page", "size"})
    return svc.listar_historial_pagina(page, size)

@router.get("/comparativa", response_model=list[ComparativaFuenteDTO])
def comparativa_fuentes(request: Request, svc: IngestaService = Depends(get_service)):
    reject_unknown_query_params(request, set())
    return svc.comparativa_fuentes()

@router.get("/sincronizaciones/export/{formato}", response_class=Response)
def exportar_sincronizaciones(formato: str, request: Request, db: Session = Depends(get_db)):
    reject_unknown_query_params(request, set())
    if formato not in {"csv", "xlsx", "pdf"}:
        raise HTTPException(status_code=422, detail="Formato de exportación inválido")
    max_rows = 1000 if formato == "pdf" else 10000
    repo = IngestaRepository(db)
    if repo.count_historial() > max_rows:
        raise HTTPException(status_code=413, detail=f"La exportación admite hasta {max_rows} registros")
    registros = repo.get_historial(limit=max_rows)
    columns = ("ID", "Fuente ID", "Inicio", "Fin", "Traídos", "Insertados", "Duplicados", "Estado", "Error")
    rows = (
        (r.id, r.fuente_id, r.fecha_inicio, r.fecha_fin, r.registros_traidos,
         r.registros_insertados, r.registros_duplicados, r.estado.value, r.mensaje_error)
        for r in registros
    )
    return render_export(columns, rows, formato, "logs_sincronizacion", "Historial de sincronizaciones")

# ── Rutas dinámicas después ────────────────────────────────────────────

@router.get("/{fuente_id}", response_model=FuenteDatosResponseDTO)
def obtener_fuente(fuente_id: int, request: Request, svc: IngestaService = Depends(get_service)):
    reject_unknown_query_params(request, set())
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

@router.post(
    "/{fuente_id}/sincronizar",
    response_model=BackgroundJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def sincronizar_fuente(fuente_id: int, db: Session = Depends(get_db)):
    fuente = IngestaRepository(db).get_by_id(fuente_id)
    if not fuente:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    if not fuente.activo:
        raise HTTPException(status_code=409, detail="La fuente está inactiva")
    job, _ = enqueue_job(
        db,
        kind="INGESTA",
        payload={"fuente_id": fuente_id},
        resource_key=f"ingesta:{fuente_id}",
    )
    return to_job_accepted(job)

@router.get("/{fuente_id}/sincronizaciones", response_model=list[SincronizacionHistorialResponseDTO])
def historial_por_fuente(fuente_id: int, request: Request, svc: IngestaService = Depends(get_service)):
    reject_unknown_query_params(request, set())
    return svc.listar_historial(fuente_id=fuente_id)

@router.get("/{fuente_id}/sincronizaciones/pagina", response_model=SincronizacionHistorialPaginaDTO)
def historial_pagina_por_fuente(
    fuente_id: int,
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    svc: IngestaService = Depends(get_service),
):
    reject_unknown_query_params(request, {"page", "size"})
    return svc.listar_historial_pagina(page, size, fuente_id=fuente_id)
