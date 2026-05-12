from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from decimal import Decimal

from core.database import SessionLocal
from modules.transformacion.dto.request import (
    ContratoProcesadoFilterDTO, AnomaliaFilterDTO, ReprocesarRequestDTO
)
from modules.transformacion.dto.response import (
    ContratoProcesadoResponseDTO, AnomaliaResponseDTO, EstadisticaCampoResponseDTO,
    PaginatedContratosDTO, PaginatedAnomaliasDTO, ReprocesarResultadoDTO,
    MetricasCalidadDTO, CampoFaltanteDTO
)
from modules.transformacion.services.trasformacionservice import TransformacionService
from modules.transformacion.repository.transformacion import TransformacionRepository

router = APIRouter(prefix="/procesados", tags=["Transformacion"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────────────
# POST /api/procesados/reprocesar
# ──────────────────────────────────────────────────────────────────────
@router.post(
    "/reprocesar",
    response_model=ReprocesarResultadoDTO,
    summary="Ejecutar pipeline de normalización",
    description=(
        "Lee registros crudos de `raw_secop`, detecta anomalías (campos faltantes, "
        "fechas futuras, montos negativos), normaliza los datos y los guarda en "
        "`contratos_procesados`. No modifica `raw_secop`. "
        "Usa `forzar_reproceso=true` para re-evaluar registros ya procesados."
    ),
)
def reprocesar(request: ReprocesarRequestDTO, db: Session = Depends(get_db)):
    service = TransformacionService(db)
    try:
        resultado = service.process_raw_data(
            limite=request.limite,
            forzar_reproceso=request.forzar_reproceso,
        )
        return ReprocesarResultadoDTO(**resultado)
    except Exception as e:
        logger_msg = str(e)
        raise HTTPException(status_code=500, detail=logger_msg)


# ──────────────────────────────────────────────────────────────────────
# GET /api/procesados/
# ──────────────────────────────────────────────────────────────────────
@router.get(
    "/",
    response_model=PaginatedContratosDTO,
    summary="Listar contratos procesados",
    description="Devuelve todos los contratos normalizados con paginación.",
)
def list_procesados(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(50, ge=1, le=1000, description="Registros por página"),
    db: Session = Depends(get_db),
):
    repo = TransformacionRepository(db)
    filters = ContratoProcesadoFilterDTO()
    skip = (page - 1) * size
    items, total = repo.search_contratos(filters=filters, skip=skip, limit=size)
    return PaginatedContratosDTO(total=total, page=page, size=size, items=items)


# ──────────────────────────────────────────────────────────────────────
# GET /api/procesados/search
# ──────────────────────────────────────────────────────────────────────
@router.get(
    "/search",
    response_model=PaginatedContratosDTO,
    summary="Buscar contratos procesados",
    description=(
        "Filtros combinables: entidad, proveedor, tipo de contrato, estado, "
        "rango de fechas de publicación y rango de valores."
    ),
)
def search_procesados(
    entidad: Optional[str] = Query(None, description="Nombre o parte de la entidad"),
    proveedor: Optional[str] = Query(None, description="Nombre o parte del proveedor"),
    tipo_contrato: Optional[str] = Query(None, description="Tipo de contrato"),
    estado: Optional[str] = Query(None, description="Estado del procedimiento"),
    fecha_inicio: Optional[date] = Query(None, description="Fecha mínima de publicación (YYYY-MM-DD)"),
    fecha_fin: Optional[date] = Query(None, description="Fecha máxima de publicación (YYYY-MM-DD)"),
    valor_min: Optional[Decimal] = Query(None, description="Valor mínimo del contrato"),
    valor_max: Optional[Decimal] = Query(None, description="Valor máximo del contrato"),
    solo_incompletos: Optional[bool] = Query(False, description="Filtrar solo contratos incompletos"),
    nivel_confianza_min: Optional[int] = Query(None, ge=0, le=100, description="Nivel de confianza mínimo"),
    nivel_confianza_max: Optional[int] = Query(None, ge=0, le=100, description="Nivel de confianza máximo"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    if nivel_confianza_min is not None and nivel_confianza_max is not None:
        if nivel_confianza_min > nivel_confianza_max:
            raise HTTPException(status_code=400, detail="nivel_confianza_min no puede ser mayor que nivel_confianza_max")

    repo = TransformacionRepository(db)
    filters = ContratoProcesadoFilterDTO(
        entidad=entidad, proveedor=proveedor,
        tipo_contrato=tipo_contrato, estado=estado,
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
        valor_min=valor_min, valor_max=valor_max,
        solo_incompletos=solo_incompletos,
        nivel_confianza_min=nivel_confianza_min,
        nivel_confianza_max=nivel_confianza_max,
    )
    skip = (page - 1) * size
    items, total = repo.search_contratos(filters=filters, skip=skip, limit=size)
    return PaginatedContratosDTO(total=total, page=page, size=size, items=items)

# ──────────────────────────────────────────────────────────────────────
# GET /api/procesados/incompletos
# ──────────────────────────────────────────────────────────────────────
@router.get(
    "/incompletos",
    response_model=PaginatedContratosDTO,
    summary="Listar contratos incompletos",
    description="Devuelve SOLO contratos incompletos con paginación.",
)
def list_incompletos(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    repo = TransformacionRepository(db)
    filters = ContratoProcesadoFilterDTO(solo_incompletos=True)
    skip = (page - 1) * size
    items, total = repo.search_contratos(filters=filters, skip=skip, limit=size)
    return PaginatedContratosDTO(total=total, page=page, size=size, items=items)


# ──────────────────────────────────────────────────────────────────────
# GET /api/procesados/{id}
# ──────────────────────────────────────────────────────────────────────
@router.get(
    "/{id}",
    response_model=ContratoProcesadoResponseDTO,
    summary="Detalle de contrato procesado",
    description="Devuelve el registro normalizado por su ID en `contratos_procesados`.",
)
def get_procesado(id: int, db: Session = Depends(get_db)):
    repo = TransformacionRepository(db)
    contrato = repo.get_contrato_by_id(id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato procesado no encontrado")
    return contrato


# ──────────────────────────────────────────────────────────────────────
# GET /api/procesados/anomalias/
# ──────────────────────────────────────────────────────────────────────
@router.get(
    "/anomalias/",
    response_model=PaginatedAnomaliasDTO,
    summary="Listar anomalías detectadas",
    description=(
        "Devuelve los registros de `contrato_anomalo_incompleto`. "
        "Filtrable por `raw_secop_id`, `motivo` (CAMPO_FALTANTE | FECHA_FUTURA | MONTO_NEGATIVO) "
        "y `campo_afectado`."
    ),
)
def list_anomalias(
    raw_secop_id: Optional[int] = Query(None, description="ID del registro crudo"),
    motivo: Optional[str] = Query(None, description="CAMPO_FALTANTE | FECHA_FUTURA | MONTO_NEGATIVO"),
    campo_afectado: Optional[str] = Query(None, description="Campo que presentó la anomalía"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    repo = TransformacionRepository(db)
    filters = AnomaliaFilterDTO(
        raw_secop_id=raw_secop_id,
        motivo=motivo,
        campo_afectado=campo_afectado,
    )
    skip = (page - 1) * size
    items, total = repo.search_anomalias(filters=filters, skip=skip, limit=size)
    return PaginatedAnomaliasDTO(total=total, page=page, size=size, items=items)


# ──────────────────────────────────────────────────────────────────────
# GET /api/procesados/estadisticas/campos-faltantes
# ──────────────────────────────────────────────────────────────────────
@router.get(
    "/estadisticas/campos-faltantes",
    response_model=list[EstadisticaCampoResponseDTO],
    summary="Estadísticas de campos faltantes",
    description=(
        "Devuelve el ranking de campos obligatorios que más frecuentemente "
        "han llegado vacíos o nulos en los datos crudos. "
        "Ordenado de mayor a menor frecuencia."
    ),
)
def get_estadisticas(db: Session = Depends(get_db)):
    repo = TransformacionRepository(db)
    return repo.get_all_estadisticas()

# ──────────────────────────────────────────────────────────────────────
# GET /api/procesados/metricas/calidad
# ──────────────────────────────────────────────────────────────────────
@router.get(
    "/metricas/calidad",
    response_model=MetricasCalidadDTO,
    summary="Métricas de calidad de datos",
    description="Resumen de contratos completos vs incompletos y sus porcentajes.",
)
def metricas_calidad(db: Session = Depends(get_db)):
    repo = TransformacionRepository(db)
    return repo.get_metricas_calidad()

# ──────────────────────────────────────────────────────────────────────
# GET /api/procesados/metricas/campos-faltantes
# ──────────────────────────────────────────────────────────────────────
@router.get(
    "/metricas/campos-faltantes",
    response_model=list[CampoFaltanteDTO],
    summary="Ranking de campos faltantes",
    description="Devuelve el conteo y porcentaje de cada campo obligatorio faltante, ordenado de mayor a menor.",
)
def metricas_campos_faltantes(db: Session = Depends(get_db)):
    repo = TransformacionRepository(db)
    estadisticas = repo.get_all_estadisticas()
    
    resultado = []
    for est in estadisticas:
        resultado.append(CampoFaltanteDTO(
            campo=est.nombre_campo,
            cantidad=est.contador_faltantes,
            porcentaje=float(est.porcentaje_total) if est.porcentaje_total else 0.0
        ))
    return resultado
