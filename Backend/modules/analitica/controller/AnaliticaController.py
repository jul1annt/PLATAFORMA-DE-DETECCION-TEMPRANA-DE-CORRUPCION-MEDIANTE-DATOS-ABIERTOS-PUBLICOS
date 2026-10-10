from uuid import UUID
import logging
import sys
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core.database import get_db
from modules.analitica.dto.request import (
    OutlierCalculoRequest, OutlierFiltroRequest,
    DuplicadoCalculoRequest, DuplicadoFiltroRequest,
    AdjudicacionDirectaCalculoRequest, AdjudicacionDirectaFiltroRequest,
    RiesgoFiltroRequest, PesoActualizarRequest,
)
from modules.analitica.dto.response import (
    RunResumenResponse, OutlierListaResponse,
    EjecucionAnaliticaEstadoResponse,
    DuplicadoResumenResponse, DuplicadoListaResponse,
    ProveedorDirectaResumenResponse, ProveedorDirectaListaResponse,
    PesoAnomaliaResponse, RiesgoProveedorListaResponse, RiesgoGlobalResumenResponse,
)
from modules.analitica.services.AnaliticaService import (
    AnaliticaService,
    EjecucionAnaliticaNoEncontradaError,
    TipoAnomaliaNoEncontradoError,
)
from modules.jobs.dto import BackgroundJobAccepted
from modules.jobs.service import enqueue_job, to_job_accepted
from gateway.middlewares.auth_middleware import get_current_admin
from shared.request_validation import reject_unknown_query_params

router = APIRouter(
    prefix="/analitica",
    tags=["Analítica"],
    dependencies=[Depends(get_current_admin)],
)


def _enqueue_analitica(db: Session, tipo: str, parametros: dict) -> BackgroundJobAccepted:
    payload = {"tipo": tipo, "parametros": parametros}
    try:
        job, created = enqueue_job(
            db,
            kind="ANALITICA",
            payload=payload,
            resource_key=f"analitica:{tipo}",
        )
        if not created and job.payload != payload:
            raise HTTPException(
                status_code=409,
                detail="Ya hay un cálculo de este tipo en curso con otros parámetros.",
            )
        return to_job_accepted(job)
    except HTTPException:
        raise
    except Exception:
        raise _internal_error("la programación del cálculo analítico")


@router.get(
    "/ejecuciones/ultimas",
    response_model=list[EjecucionAnaliticaEstadoResponse],
    summary="Consultar el estado de las últimas ejecuciones analíticas",
)
def obtener_estados_ultimas_ejecuciones(db: Session = Depends(get_db)):
    try:
        return AnaliticaService(db).obtener_estados_ultimas_ejecuciones()
    except Exception:
        raise _internal_error("la consulta de estados analíticos")


def _internal_error(operation: str) -> HTTPException:
    active_error = sys.exception()
    error_id = str(getattr(active_error, "error_id", None) or uuid.uuid4())
    exception_type = type(active_error).__name__ if active_error is not None else "Desconocida"
    logging.getLogger(__name__).error(
        "Fallo en %s. Referencia %s. Tipo de excepción %s",
        operation,
        error_id,
        exception_type,
    )
    return HTTPException(
        status_code=500,
        detail=f"Error interno durante {operation}. Referencia: {error_id}",
    )


@router.post(
    "/outliers/calcular",
    response_model=BackgroundJobAccepted,
    status_code=202,
    summary="Ejecutar análisis IQR de outliers",
    description=(
        "Dispara el algoritmo IQR sobre contratos_procesados. "
        "Agrupa por modalidad de contratación (fallback: tipo de contrato), "
        "calcula Q1/Q3/IQR con percentile_cont() de PostgreSQL, "
        "clasifica cada contrato y persiste el resultado en contrato_outlier. "
        "Retorna el identificador del trabajo para consultar su estado y resultado."
    ),
)
def calcular_outliers(
    body: OutlierCalculoRequest,
    db: Session = Depends(get_db),
):
    return _enqueue_analitica(db, "OUTLIERS", body.model_dump(mode="json"))


@router.get(
    "/outliers",
    response_model=OutlierListaResponse,
    summary="Listar contratos analizados",
    description=(
        "Retorna los contratos del análisis con filtros opcionales. "
        "Si no se pasa run_id se usa la última ejecución. "
        "Usa solo_outliers=true para el filtro del dashboard."
    ),
)
def listar_outliers(
    request: Request,
    run_id: UUID | None = Query(default=None, description="UUID de la ejecución. Default: última."),
    solo_outliers: bool = Query(default=False, description="True = solo contratos marcados como outlier."),
    grupo: str | None = Query(default=None, description="Filtrar por modalidad o tipo de contrato."),
    direccion: str | None = Query(default=None, pattern="^(ALTO|BAJO)$", description="'ALTO' o 'BAJO'."),
    score_minimo: float | None = Query(default=None, ge=0, allow_inf_nan=False, description="Score mínimo."),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    reject_unknown_query_params(
        request,
        {"run_id", "solo_outliers", "grupo", "direccion", "score_minimo", "page", "page_size"},
    )
    try:
        filtros = OutlierFiltroRequest(
            run_id=str(run_id) if run_id else None,
            solo_outliers=solo_outliers,
            grupo=grupo,
            direccion=direccion,
            score_minimo=score_minimo,
            page=page,
            page_size=page_size,
        )
        service = AnaliticaService(db)
        return service.listar_outliers(filtros)
    except EjecucionAnaliticaNoEncontradaError:
        raise HTTPException(status_code=404, detail="No hay una ejecución de outliers disponible.")
    except Exception:
        raise _internal_error("la consulta de outliers")


@router.get(
    "/outliers/resumen",
    response_model=RunResumenResponse,
    summary="Resumen de la última ejecución (dashboard)",
    description=(
        "Retorna totales, porcentaje de outliers y estadísticas por grupo. "
        "Es el endpoint principal del widget de métricas del dashboard."
    ),
)
def obtener_resumen_ultimo(request: Request, db: Session = Depends(get_db)):
    reject_unknown_query_params(request, set())
    try:
        service = AnaliticaService(db)
        ultimo_run_id = service.repo.obtener_ultimo_run_id()
        if not ultimo_run_id:
            raise EjecucionAnaliticaNoEncontradaError("No hay ejecución de outliers.")
        return service.obtener_resumen(ultimo_run_id)
    except EjecucionAnaliticaNoEncontradaError:
        raise HTTPException(status_code=404, detail="No hay una ejecución de outliers disponible.")
    except Exception:
        raise _internal_error("la consulta del resumen de outliers")


@router.get(
    "/outliers/resumen/{run_id}",
    response_model=RunResumenResponse,
    summary="Resumen de una ejecución específica",
)
def obtener_resumen_por_run(request: Request, run_id: UUID, db: Session = Depends(get_db)):
    reject_unknown_query_params(request, set())
    try:
        service = AnaliticaService(db)
        return service.obtener_resumen(run_id)
    except Exception:
        raise _internal_error("la consulta del resumen de outliers")


# ====================================================================
# ENDPOINTS: DUPLICADOS EN PERÍODO CORTO
# ====================================================================

@router.post(
    "/duplicados/calcular",
    response_model=BackgroundJobAccepted,
    status_code=202,
    summary="Ejecutar análisis de duplicados en período corto",
    description=(
        "Busca contratos del mismo proveedor, misma entidad y características similares "
        "(mismo tipo o modalidad) que tengan una diferencia de fechas <= 30 días. "
        "Asigna un score y nivel de riesgo, guarda los resultados y devuelve el trabajo encolado."
    ),
)
def calcular_duplicados(
    body: DuplicadoCalculoRequest,
    db: Session = Depends(get_db),
):
    return _enqueue_analitica(db, "DUPLICADOS", body.model_dump(mode="json"))


@router.get(
    "/duplicados",
    response_model=DuplicadoListaResponse,
    summary="Listar contratos duplicados detectados",
    description="Retorna los contratos duplicados del análisis con filtros opcionales.",
)
def listar_duplicados(
    request: Request,
    run_id: UUID | None = Query(default=None, description="UUID de la ejecución. Default: última."),
    riesgo: str | None = Query(default=None, pattern="^(ALTO|MEDIO|BAJO)$", description="Filtrar por riesgo: ALTO, MEDIO, BAJO."),
    score_minimo: float | None = Query(default=None, ge=0, allow_inf_nan=False, description="Score mínimo."),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    reject_unknown_query_params(request, {"run_id", "riesgo", "score_minimo", "page", "page_size"})
    try:
        filtros = DuplicadoFiltroRequest(
            run_id=str(run_id) if run_id else None,
            riesgo=riesgo,
            score_minimo=score_minimo,
            page=page,
            page_size=page_size,
        )
        service = AnaliticaService(db)
        return service.listar_duplicados(filtros)
    except EjecucionAnaliticaNoEncontradaError:
        raise HTTPException(status_code=404, detail="No hay una ejecución de duplicados disponible.")
    except Exception:
        raise _internal_error("la consulta de duplicados")


@router.get(
    "/duplicados/resumen",
    response_model=DuplicadoResumenResponse,
    summary="Resumen de la última ejecución de duplicados (dashboard)",
)
def obtener_resumen_duplicados_ultimo(request: Request, db: Session = Depends(get_db)):
    reject_unknown_query_params(request, set())
    try:
        service = AnaliticaService(db)
        ultimo_run_id = service.repo.obtener_ultimo_run_id_duplicados()
        if not ultimo_run_id:
            raise EjecucionAnaliticaNoEncontradaError("No hay ejecución de duplicados.")
        return service.obtener_resumen_duplicados(ultimo_run_id)
    except EjecucionAnaliticaNoEncontradaError:
        raise HTTPException(status_code=404, detail="No hay una ejecución de duplicados disponible.")
    except Exception:
        raise _internal_error("la consulta del resumen de duplicados")


@router.get(
    "/duplicados/resumen/{run_id}",
    response_model=DuplicadoResumenResponse,
    summary="Resumen de una ejecución específica de duplicados",
)
def obtener_resumen_duplicados_por_run(request: Request, run_id: UUID, db: Session = Depends(get_db)):
    reject_unknown_query_params(request, set())
    try:
        service = AnaliticaService(db)
        return service.obtener_resumen_duplicados(run_id)
    except Exception:
        raise _internal_error("la consulta del resumen de duplicados")


# ====================================================================
# ENDPOINTS: ABUSO DE ADJUDICACIÓN DIRECTA
# ====================================================================

@router.post(
    "/directas/calcular",
    response_model=BackgroundJobAccepted,
    status_code=202,
    summary="Ejecutar análisis de abuso de adjudicación directa",
    description=(
        "Detecta proveedores con más contratos directos que el umbral configurado. "
        "Agrupa por proveedor, calcula porcentaje de directas, score y clasificación de riesgo. "
        "Persiste los resultados en proveedor_adjudicacion_directa desde un trabajo en segundo plano."
    ),
)
def calcular_adjudicaciones_directas(
    body: AdjudicacionDirectaCalculoRequest,
    db: Session = Depends(get_db),
):
    return _enqueue_analitica(db, "ADJUDICACION_DIRECTA", body.model_dump(mode="json"))


@router.get(
    "/directas",
    response_model=ProveedorDirectaListaResponse,
    summary="Listar proveedores con abuso de adjudicación directa",
    description=(
        "Retorna los proveedores detectados con filtros opcionales. "
        "Si no se pasa run_id se usa la última ejecución. "
        "Usa solo_abuso_directas=true para el filtro del dashboard (solo ALTO y MEDIO)."
    ),
)
def listar_adjudicaciones_directas(
    request: Request,
    run_id: UUID | None = Query(default=None, description="UUID de la ejecución. Default: última."),
    riesgo: str | None = Query(default=None, pattern="^(ALTO|MEDIO|BAJO)$", description="Filtrar por riesgo: ALTO, MEDIO, BAJO."),
    score_minimo: float | None = Query(default=None, ge=0, allow_inf_nan=False, description="Score mínimo."),
    score_maximo: float | None = Query(default=None, ge=0, allow_inf_nan=False, description="Score máximo."),
    porcentaje_minimo: float | None = Query(default=None, ge=0, le=100, allow_inf_nan=False, description="Porcentaje mínimo de directas."),
    porcentaje_maximo: float | None = Query(default=None, ge=0, le=100, allow_inf_nan=False, description="Porcentaje máximo de directas."),
    solo_abuso_directas: bool = Query(default=False, description="True = solo ALTO y MEDIO."),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    reject_unknown_query_params(
        request,
        {
            "run_id", "riesgo", "score_minimo", "score_maximo", "porcentaje_minimo",
            "porcentaje_maximo", "solo_abuso_directas", "page", "page_size",
        },
    )
    if score_minimo is not None and score_maximo is not None and score_minimo > score_maximo:
        raise HTTPException(status_code=422, detail="score_minimo no puede ser mayor que score_maximo")
    if (
        porcentaje_minimo is not None
        and porcentaje_maximo is not None
        and porcentaje_minimo > porcentaje_maximo
    ):
        raise HTTPException(status_code=422, detail="porcentaje_minimo no puede ser mayor que porcentaje_maximo")
    try:
        filtros = AdjudicacionDirectaFiltroRequest(
            run_id=str(run_id) if run_id else None,
            riesgo=riesgo,
            score_minimo=score_minimo,
            score_maximo=score_maximo,
            porcentaje_minimo=porcentaje_minimo,
            porcentaje_maximo=porcentaje_maximo,
            solo_abuso_directas=solo_abuso_directas,
            page=page,
            page_size=page_size,
        )
        service = AnaliticaService(db)
        return service.listar_directas(filtros)
    except EjecucionAnaliticaNoEncontradaError:
        raise HTTPException(status_code=404, detail="No hay una ejecución de adjudicaciones directas disponible.")
    except Exception:
        raise _internal_error("la consulta de adjudicaciones directas")


@router.get(
    "/directas/resumen",
    response_model=ProveedorDirectaResumenResponse,
    summary="Resumen de la última ejecución de adjudicaciones directas (dashboard)",
)
def obtener_resumen_directas_ultimo(request: Request, db: Session = Depends(get_db)):
    reject_unknown_query_params(request, set())
    try:
        service = AnaliticaService(db)
        ultimo_run_id = service.repo.obtener_ultimo_run_id_directas()
        if not ultimo_run_id:
            raise EjecucionAnaliticaNoEncontradaError("No hay ejecución de adjudicaciones directas.")
        return service.obtener_resumen_directas(ultimo_run_id)
    except EjecucionAnaliticaNoEncontradaError:
        raise HTTPException(status_code=404, detail="No hay una ejecución de adjudicaciones directas disponible.")
    except Exception:
        raise _internal_error("la consulta del resumen de adjudicaciones directas")


@router.get(
    "/directas/resumen/{run_id}",
    response_model=ProveedorDirectaResumenResponse,
    summary="Resumen de una ejecución específica de adjudicaciones directas",
)
def obtener_resumen_directas_por_run(request: Request, run_id: UUID, db: Session = Depends(get_db)):
    reject_unknown_query_params(request, set())
    try:
        service = AnaliticaService(db)
        return service.obtener_resumen_directas(run_id)
    except Exception:
        raise _internal_error("la consulta del resumen de adjudicaciones directas")


# ====================================================================
# ENDPOINTS: CONFIGURACIÓN DE PESOS
# ====================================================================

@router.get(
    "/pesos",
    response_model=list[PesoAnomaliaResponse],
    summary="Obtener pesos de anomalías",
    description="Devuelve la configuración actual de pesos para el cálculo de riesgo combinado.",
)
def obtener_pesos(request: Request, db: Session = Depends(get_db)):
    reject_unknown_query_params(request, set())
    try:
        service = AnaliticaService(db)
        return service.obtener_pesos()
    except Exception:
        raise _internal_error("la consulta de pesos")

@router.put(
    "/pesos/{tipo_anomalia}",
    response_model=PesoAnomaliaResponse,
    summary="Actualizar el peso de una anomalía",
    description="Actualiza el peso que se utilizará en futuros cálculos de riesgo combinado.",
)
def actualizar_peso(
    tipo_anomalia: str,
    body: PesoActualizarRequest,
    db: Session = Depends(get_db),
):
    try:
        service = AnaliticaService(db)
        return service.actualizar_peso(tipo_anomalia, body)
    except TipoAnomaliaNoEncontradoError:
        raise HTTPException(status_code=404, detail="Tipo de anomalía no encontrado.")
    except Exception:
        raise _internal_error("la actualización de pesos")


# ====================================================================
# ENDPOINTS: RIESGO COMBINADO POR PROVEEDOR
# ====================================================================

@router.post(
    "/riesgo/calcular",
    response_model=BackgroundJobAccepted,
    status_code=202,
    summary="Ejecutar cálculo de riesgo global combinado",
    description=(
        "Cruza los scores más recientes de outliers, duplicados y adjudicación directa. "
        "Aplica los pesos configurados y clasifica el riesgo del proveedor en un trabajo en segundo plano. "
        "El trabajo termina con error si falta alguna ejecución componente compatible."
    ),
)
def calcular_riesgo_global(db: Session = Depends(get_db)):
    return _enqueue_analitica(db, "RIESGO", {})

@router.get(
    "/riesgo",
    response_model=RiesgoProveedorListaResponse,
    summary="Listar proveedores con riesgo combinado",
    description="Retorna el listado de proveedores evaluados con sus scores combinados.",
)
def listar_riesgos(
    request: Request,
    run_id: UUID | None = Query(default=None, description="UUID de la ejecución. Default: última."),
    proveedor: str | None = Query(default=None, description="Filtrar por nombre de proveedor."),
    riesgo: str | None = Query(default=None, pattern="^(ALTO|MEDIO|BAJO)$", description="Filtrar por riesgo: ALTO, MEDIO, BAJO."),
    score_minimo: float | None = Query(default=None, ge=0, allow_inf_nan=False, description="Score final mínimo."),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    reject_unknown_query_params(request, {"run_id", "proveedor", "riesgo", "score_minimo", "page", "page_size"})
    try:
        filtros = RiesgoFiltroRequest(
            run_id=str(run_id) if run_id else None,
            proveedor=proveedor,
            riesgo=riesgo,
            score_minimo=score_minimo,
            page=page,
            page_size=page_size,
        )
        service = AnaliticaService(db)
        return service.listar_riesgos(filtros)
    except EjecucionAnaliticaNoEncontradaError:
        raise HTTPException(status_code=404, detail="No hay una ejecución de riesgo disponible.")
    except Exception:
        raise _internal_error("la consulta de riesgos")

@router.get(
    "/riesgo/resumen",
    response_model=RiesgoGlobalResumenResponse,
    summary="Resumen de la última ejecución de riesgo global",
)
def obtener_resumen_riesgo_ultimo(request: Request, db: Session = Depends(get_db)):
    reject_unknown_query_params(request, set())
    try:
        service = AnaliticaService(db)
        ultimo_run_id = service.repo.obtener_ultimo_run_id_riesgo()
        if not ultimo_run_id:
            raise EjecucionAnaliticaNoEncontradaError("No hay ejecución de riesgo.")
        return service.obtener_resumen_riesgo(ultimo_run_id)
    except EjecucionAnaliticaNoEncontradaError:
        raise HTTPException(status_code=404, detail="No hay una ejecución de riesgo disponible.")
    except Exception:
        raise _internal_error("la consulta del resumen de riesgo")

