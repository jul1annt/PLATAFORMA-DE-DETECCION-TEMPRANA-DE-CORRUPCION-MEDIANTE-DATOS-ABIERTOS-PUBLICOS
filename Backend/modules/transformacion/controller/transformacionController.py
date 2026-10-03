from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from pydantic import ValidationError
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime, timezone
from decimal import Decimal
import logging
import time
import uuid

from core.config import settings
from core.database import get_db
from modules.transformacion.dto.request import (
    ContratoProcesadoFilterDTO, AnomaliaFilterDTO, ReprocesarRequestDTO
)
from modules.transformacion.dto.response import (
    ContratoProcesadoResponseDTO, AnomaliaResponseDTO, EstadisticaCampoResponseDTO,
    PaginatedContratosDTO, PaginatedAnomaliasDTO,
    MetricasCalidadDTO, CampoFaltanteDTO, PaginatedProcesamientoLogsDTO,
    DashboardMetricasDTO, DistribucionDTO, TopProveedorDTO, AutocompleteDTO,
)
from modules.transformacion.repository.transformacion import TransformacionRepository
from gateway.middlewares.auth_middleware import get_current_admin
from shared.exporting import render_export
from modules.jobs.dto import BackgroundJobAccepted, ExportJobAccepted
from modules.jobs.service import enqueue_job, to_job_accepted
from shared.export_artifacts import create_export_token
from shared.request_validation import reject_unknown_query_params as _validar_query_params

router = APIRouter(prefix="/procesados", tags=["Transformacion"])


# ──────────────────────────────────────────────────────────────────────
# POST /api/procesados/reprocesar
# ──────────────────────────────────────────────────────────────────────
@router.post(
    "/reprocesar",
    response_model=BackgroundJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ejecutar pipeline de normalización",
    description=(
        "Lee registros crudos de `raw_secop`, detecta anomalías (campos faltantes, "
        "fechas futuras, montos negativos), normaliza los datos y los guarda en "
        "`contratos_procesados`. No modifica `raw_secop`. "
        "Usa `forzar_reproceso=true` para re-evaluar registros ya procesados."
    ),
    dependencies=[Depends(get_current_admin)],
)
def reprocesar(request: ReprocesarRequestDTO, db: Session = Depends(get_db)):
    job, _ = enqueue_job(
        db,
        kind="REPROCESAMIENTO",
        payload={"forzar_reproceso": request.forzar_reproceso},
        resource_key="transformacion:global",
    )
    return to_job_accepted(job)


# ──────────────────────────────────────────────────────────────────────
# GET /api/procesados/logs
# ──────────────────────────────────────────────────────────────────────
@router.get(
    "/logs",
    response_model=PaginatedProcesamientoLogsDTO,
    summary="Listar historial de ejecuciones",
    description="Devuelve los logs de ejecución del pipeline de normalización, ordenados por los más recientes.",
    dependencies=[Depends(get_current_admin)],
)
def list_logs(
    request: Request,
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Registros por página"),
    db: Session = Depends(get_db),
):
    _validar_query_params(request, {"page", "size"})
    repo = TransformacionRepository(db)
    skip = (page - 1) * size
    items, total = repo.search_logs(skip=skip, limit=size)
    return PaginatedProcesamientoLogsDTO(total=total, page=page, size=size, items=items)


@router.get("/logs/export/{formato}", response_class=Response, dependencies=[Depends(get_current_admin)])
def exportar_logs_procesamiento(formato: str, request: Request, db: Session = Depends(get_db)):
    _validar_query_params(request, set())
    if formato not in {"csv", "xlsx", "pdf"}:
        raise HTTPException(status_code=422, detail="Formato de exportación inválido")
    max_rows = 1000 if formato == "pdf" else 10000
    logs, total = TransformacionRepository(db).search_logs(limit=max_rows)
    if total > max_rows:
        raise HTTPException(status_code=413, detail=f"La exportación admite hasta {max_rows} registros")
    columns = ("ID", "Estado", "Forzar", "Inicio", "Fin", "Duración", "Evaluados", "Procesados", "Omitidos", "Anomalías", "Error")
    rows = (
        (log.id, log.estado, log.forzar_reproceso, log.fecha_hora_inicio,
         log.fecha_hora_fin, log.duracion_segundos, log.total_evaluados,
         log.procesados, log.omitidos, log.anomalias_registradas, log.mensaje_error)
        for log in logs
    )
    return render_export(columns, rows, formato, "historial_reprocesamiento", "Historial de reprocesamiento")

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
    request: Request,
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(50, ge=1, le=1000, description="Registros por página"),
    db: Session = Depends(get_db),
):
    _validar_query_params(request, {"page", "size"})
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
    request: Request,
    entidad: Optional[str] = Query(None, description="Nombre o parte de la entidad"),
    proveedor: Optional[str] = Query(None, description="Nombre o parte del proveedor"),
    modalidad: Optional[str] = Query(None, description="Modalidad de contratación"),
    estado: Optional[str] = Query(None, description="Estado del procedimiento"),
    fecha_inicio: Optional[date] = Query(None, description="Fecha mínima de publicación (YYYY-MM-DD)"),
    fecha_fin: Optional[date] = Query(None, description="Fecha máxima de publicación (YYYY-MM-DD)"),
    valor_min: Optional[Decimal] = Query(None, ge=0, description="Valor mínimo del contrato"),
    valor_max: Optional[Decimal] = Query(None, ge=0, description="Valor máximo del contrato"),
    solo_incompletos: Optional[bool] = Query(False, description="Filtrar solo contratos incompletos"),
    solo_sospechosos: Optional[bool] = Query(False, description="Filtrar solo contratos sospechosos"),
    nivel_confianza_min: Optional[int] = Query(None, ge=0, le=100, description="Nivel de confianza mínimo"),
    nivel_confianza_max: Optional[int] = Query(None, ge=0, le=100, description="Nivel de confianza máximo"),
    q: Optional[str] = Query(None, min_length=2, max_length=200, description="Texto en entidad, proveedor, NIT o proceso"),
    solo_alto_riesgo: bool = Query(False),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, pattern="^(valor|valor_total_normalizado|precio_base_normalizado|fecha|id|entidad|proveedor|riesgo)$", description="Campo por el cual ordenar"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    allowed_query_params = {
        "entidad", "proveedor", "modalidad", "estado", "fecha_inicio", "fecha_fin",
        "valor_min", "valor_max", "solo_incompletos", "solo_sospechosos",
        "nivel_confianza_min", "nivel_confianza_max", "q", "solo_alto_riesgo",
        "limit", "offset", "sort", "order",
    }
    _validar_query_params(request, allowed_query_params)

    if nivel_confianza_min is not None and nivel_confianza_max is not None:
        if nivel_confianza_min > nivel_confianza_max:
            raise HTTPException(status_code=400, detail="nivel_confianza_min no puede ser mayor que nivel_confianza_max")
    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        raise HTTPException(status_code=400, detail="fecha_inicio no puede ser mayor que fecha_fin")
    if valor_min is not None and valor_max is not None and valor_min > valor_max:
        raise HTTPException(status_code=400, detail="valor_min no puede ser mayor que valor_max")

    repo = TransformacionRepository(db)
    filters = ContratoProcesadoFilterDTO(
        entidad=entidad, proveedor=proveedor,
        modalidad=modalidad, estado=estado,
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
        valor_min=valor_min, valor_max=valor_max,
        solo_incompletos=solo_incompletos,
        solo_sospechosos=solo_sospechosos,
        nivel_confianza_min=nivel_confianza_min,
        nivel_confianza_max=nivel_confianza_max,
        query=q,
        solo_alto_riesgo=solo_alto_riesgo,
    )
    items, total = repo.search_contratos(filters=filters, skip=offset, limit=limit, sort=sort, order=order)
    page = (offset // limit) + 1
    return PaginatedContratosDTO(total=total, page=page, size=limit, items=items)


def _parse_export_filters(request: Request) -> tuple[ContratoProcesadoFilterDTO, str | None, str]:
    allowed = set(ContratoProcesadoFilterDTO.model_fields) - {"query"}
    allowed.update({"q", "limit", "offset", "sort", "order"})
    _validar_query_params(request, allowed)
    params = dict(request.query_params)
    params["query"] = params.pop("q", None)
    sort = params.pop("sort", None)
    order = params.pop("order", "desc")
    params.pop("limit", None)
    params.pop("offset", None)
    valid_sort = {None, "valor", "valor_total_normalizado", "precio_base_normalizado", "fecha", "id", "entidad", "proveedor", "riesgo"}
    if sort not in valid_sort or order not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="Orden de exportación inválido")
    try:
        filters = ContratoProcesadoFilterDTO.model_validate(params)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    if filters.fecha_inicio and filters.fecha_fin and filters.fecha_inicio > filters.fecha_fin:
        raise HTTPException(status_code=422, detail="Rango de fechas inválido")
    if filters.valor_min is not None and filters.valor_max is not None and filters.valor_min > filters.valor_max:
        raise HTTPException(status_code=422, detail="Rango de valores inválido")
    if filters.nivel_confianza_min is not None and filters.nivel_confianza_max is not None and filters.nivel_confianza_min > filters.nivel_confianza_max:
        raise HTTPException(status_code=422, detail="Rango de confianza inválido")
    return filters, sort, order


@router.post(
    "/export/{formato}/jobs",
    response_model=ExportJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Crear una exportación descargable",
)
def crear_exportacion_contratos(
    formato: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    if formato not in {"csv", "xlsx", "pdf"}:
        raise HTTPException(status_code=422, detail="Formato de exportación inválido")
    filters, sort, order = _parse_export_filters(request)
    _, total = TransformacionRepository(db).search_contratos(
        filters,
        skip=0,
        limit=1,
        sort=sort,
        order=order,
    )
    if total == 0:
        raise HTTPException(status_code=422, detail="No hay contratos para exportar")
    row_limit = min(settings.EXPORT_MAX_ROWS, 1000) if formato == "pdf" else settings.EXPORT_MAX_ROWS
    if total > row_limit:
        raise HTTPException(
            status_code=413,
            detail=f"La exportación admite hasta {row_limit} registros. Acota los filtros.",
        )

    expires_at = int(time.time()) + settings.EXPORT_CAPABILITY_TTL_HOURS * 60 * 60
    payload = {
        "format": formato,
        "filters": filters.model_dump(mode="json"),
        "sort": sort,
        "order": order,
        "expires_at": expires_at,
    }
    job, _ = enqueue_job(
        db,
        kind="EXPORTACION_CONTRATOS",
        payload=payload,
        resource_key=f"exportacion:{uuid.uuid4()}",
    )
    token = create_export_token(job.public_id, expires_at)
    return ExportJobAccepted(
        id=job.public_id,
        status=job.status,
        access_token=token,
        status_url=f"/api/exports/{job.public_id}",
        download_url=f"/api/exports/{job.public_id}/download",
        expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc),
    )


@router.get("/export/{formato}", response_class=Response)
def exportar_contratos(
    formato: str,
    request: Request,
    db: Session = Depends(get_db),
):
    if formato not in {"csv", "xlsx", "pdf"}:
        raise HTTPException(status_code=422, detail="Formato de exportación inválido")
    filters, sort, order = _parse_export_filters(request)

    max_rows = 1000 if formato == "pdf" else 10000
    items, total = TransformacionRepository(db).search_contratos(
        filters, skip=0, limit=max_rows, sort=sort, order=order
    )
    if total > max_rows:
        raise HTTPException(
            status_code=413,
            detail=f"La exportación admite hasta {max_rows} registros. Acota los filtros.",
        )
    columns = ("ID", "Entidad", "Proveedor", "Modalidad", "Valor total", "Fecha publicación", "Estado", "Confianza", "Incompleto", "Sospechoso", "Riesgo")
    rows = (
        (
            item.id, item.entidad_normalizada, item.proveedor_normalizado,
            item.modalidad_contratacion, item.valor_total_normalizado,
            item.fecha_publicacion_normalizada, item.estado_normalizado,
            item.nivel_confianza, item.es_incompleto, item.es_sospechoso,
            item.clasificacion_riesgo,
        )
        for item in items
    )
    return render_export(columns, rows, formato, "contratos_calidad", "Contratos procesados")


@router.get("/autocomplete", response_model=list[AutocompleteDTO])
def autocomplete(
    request: Request,
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    _validar_query_params(request, {"q", "limit"})
    return TransformacionRepository(db).autocomplete(q, limit)


@router.get("/metricas/dashboard", response_model=DashboardMetricasDTO)
def dashboard_metricas(request: Request, db: Session = Depends(get_db)):
    _validar_query_params(request, set())
    return TransformacionRepository(db).get_dashboard_metricas()


@router.get("/metricas/distribucion-riesgo", response_model=list[DistribucionDTO])
def distribucion_riesgo(request: Request, db: Session = Depends(get_db)):
    _validar_query_params(request, set())
    return TransformacionRepository(db).get_risk_distribution()


@router.get("/metricas/distribucion-anomalias", response_model=list[DistribucionDTO])
def distribucion_anomalias(request: Request, db: Session = Depends(get_db)):
    _validar_query_params(request, set())
    return TransformacionRepository(db).get_anomaly_distribution()


@router.get("/metricas/top-proveedores", response_model=list[TopProveedorDTO])
def top_proveedores(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    _validar_query_params(request, {"limit"})
    return TransformacionRepository(db).get_top_providers(limit)

# ──────────────────────────────────────────────────────────────────────
# GET /api/procesados/sospechosos
# ──────────────────────────────────────────────────────────────────────
@router.get(
    "/sospechosos",
    response_model=PaginatedContratosDTO,
    summary="Listar contratos sospechosos",
    description="Devuelve SOLO contratos con valores sospechosos (fechas futuras, etc.) con paginación.",
)
def list_sospechosos(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    _validar_query_params(request, {"page", "size"})
    repo = TransformacionRepository(db)
    filters = ContratoProcesadoFilterDTO(solo_sospechosos=True)
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
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    _validar_query_params(request, {"page", "size"})
    repo = TransformacionRepository(db)
    filters = ContratoProcesadoFilterDTO(solo_incompletos=True)
    skip = (page - 1) * size
    items, total = repo.search_contratos(filters=filters, skip=skip, limit=size)
    return PaginatedContratosDTO(total=total, page=page, size=size, items=items)


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
    request: Request,
    raw_secop_id: Optional[int] = Query(None, ge=1, description="ID del registro crudo"),
    motivo: Optional[str] = Query(None, pattern="^(CAMPO_FALTANTE|FECHA_FUTURA|MONTO_NEGATIVO)$", description="CAMPO_FALTANTE | FECHA_FUTURA | MONTO_NEGATIVO"),
    campo_afectado: Optional[str] = Query(None, min_length=1, max_length=200, description="Campo que presentó la anomalía"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    _validar_query_params(request, {"raw_secop_id", "motivo", "campo_afectado", "page", "size"})
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
def get_estadisticas(request: Request, db: Session = Depends(get_db)):
    _validar_query_params(request, set())
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
def metricas_calidad(request: Request, db: Session = Depends(get_db)):
    _validar_query_params(request, set())
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
def metricas_campos_faltantes(request: Request, db: Session = Depends(get_db)):
    _validar_query_params(request, set())
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


# Esta ruta dinámica debe declararse después de todas las rutas estáticas.
@router.get(
    "/{id}",
    response_model=ContratoProcesadoResponseDTO,
    summary="Detalle de contrato procesado",
    description="Devuelve el registro normalizado por su ID en `contratos_procesados`.",
)
def get_procesado(
    request: Request,
    id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    _validar_query_params(request, set())
    contrato = TransformacionRepository(db).get_contrato_by_id(id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato procesado no encontrado")
    return contrato
