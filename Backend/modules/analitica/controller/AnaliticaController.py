from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.dependencies import get_db
from modules.analitica.dto.request import (
    OutlierCalculoRequest, OutlierFiltroRequest,
    DuplicadoCalculoRequest, DuplicadoFiltroRequest,
    AdjudicacionDirectaCalculoRequest, AdjudicacionDirectaFiltroRequest,
    RiesgoFiltroRequest, PesoActualizarRequest,
)
from modules.analitica.dto.response import (
    RunResumenResponse, OutlierListaResponse,
    DuplicadoResumenResponse, DuplicadoListaResponse,
    ProveedorDirectaResumenResponse, ProveedorDirectaListaResponse,
    PesoAnomaliaResponse, RiesgoProveedorListaResponse, RiesgoGlobalResumenResponse,
)
from modules.analitica.services.AnaliticaService import AnaliticaService

router = APIRouter(prefix="/analitica", tags=["Analítica"])


@router.post(
    "/outliers/calcular",
    response_model=RunResumenResponse,
    summary="Ejecutar análisis IQR de outliers",
    description=(
        "Dispara el algoritmo IQR sobre contratos_procesados. "
        "Agrupa por modalidad de contratación (fallback: tipo de contrato), "
        "calcula Q1/Q3/IQR con percentile_cont() de PostgreSQL, "
        "clasifica cada contrato y persiste el resultado en contrato_outlier. "
        "Retorna el resumen de la ejecución."
    ),
)
def calcular_outliers(
    body: OutlierCalculoRequest,
    db: Session = Depends(get_db),
):
    try:
        service = AnaliticaService(db)
        return service.calcular_outliers(body)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular outliers: {str(e)}")


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
    run_id: str | None = Query(default=None, description="UUID de la ejecución. Default: última."),
    solo_outliers: bool = Query(default=False, description="True = solo contratos marcados como outlier."),
    grupo: str | None = Query(default=None, description="Filtrar por modalidad o tipo de contrato."),
    direccion: str | None = Query(default=None, description="'ALTO' o 'BAJO'."),
    score_minimo: float | None = Query(default=None, ge=0, description="Score mínimo."),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        filtros = OutlierFiltroRequest(
            run_id=run_id,
            solo_outliers=solo_outliers,
            grupo=grupo,
            direccion=direccion,
            score_minimo=score_minimo,
            page=page,
            page_size=page_size,
        )
        service = AnaliticaService(db)
        return service.listar_outliers(filtros)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar outliers: {str(e)}")


@router.get(
    "/outliers/resumen",
    response_model=RunResumenResponse,
    summary="Resumen de la última ejecución (dashboard)",
    description=(
        "Retorna totales, porcentaje de outliers y estadísticas por grupo. "
        "Es el endpoint principal del widget de métricas del dashboard."
    ),
)
def obtener_resumen_ultimo(db: Session = Depends(get_db)):
    try:
        service = AnaliticaService(db)
        ultimo_run_id = service.repo.obtener_ultimo_run_id()
        if not ultimo_run_id:
            raise ValueError("No existe ninguna ejecución registrada.")
        return service.obtener_resumen(ultimo_run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen: {str(e)}")


@router.get(
    "/outliers/resumen/{run_id}",
    response_model=RunResumenResponse,
    summary="Resumen de una ejecución específica",
)
def obtener_resumen_por_run(run_id: UUID, db: Session = Depends(get_db)):
    try:
        service = AnaliticaService(db)
        return service.obtener_resumen(run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen del run {run_id}: {str(e)}")


# ====================================================================
# ENDPOINTS: DUPLICADOS EN PERÍODO CORTO
# ====================================================================

@router.post(
    "/duplicados/calcular",
    response_model=DuplicadoResumenResponse,
    summary="Ejecutar análisis de duplicados en período corto",
    description=(
        "Busca contratos del mismo proveedor, misma entidad y características similares "
        "(mismo tipo o modalidad) que tengan una diferencia de fechas <= 30 días. "
        "Asigna un score y nivel de riesgo, y guarda los resultados."
    ),
)
def calcular_duplicados(
    body: DuplicadoCalculoRequest,
    db: Session = Depends(get_db),
):
    try:
        service = AnaliticaService(db)
        return service.calcular_duplicados(body)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular duplicados: {str(e)}")


@router.get(
    "/duplicados",
    response_model=DuplicadoListaResponse,
    summary="Listar contratos duplicados detectados",
    description="Retorna los contratos duplicados del análisis con filtros opcionales.",
)
def listar_duplicados(
    run_id: str | None = Query(default=None, description="UUID de la ejecución. Default: última."),
    riesgo: str | None = Query(default=None, description="Filtrar por riesgo: ALTO, MEDIO, BAJO."),
    score_minimo: float | None = Query(default=None, ge=0, description="Score mínimo."),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        filtros = DuplicadoFiltroRequest(
            run_id=run_id,
            riesgo=riesgo,
            score_minimo=score_minimo,
            page=page,
            page_size=page_size,
        )
        service = AnaliticaService(db)
        return service.listar_duplicados(filtros)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar duplicados: {str(e)}")


@router.get(
    "/duplicados/resumen",
    response_model=DuplicadoResumenResponse,
    summary="Resumen de la última ejecución de duplicados (dashboard)",
)
def obtener_resumen_duplicados_ultimo(db: Session = Depends(get_db)):
    try:
        service = AnaliticaService(db)
        ultimo_run_id = service.repo.obtener_ultimo_run_id_duplicados()
        if not ultimo_run_id:
            raise ValueError("No existe ninguna ejecución de duplicados registrada.")
        return service.obtener_resumen_duplicados(ultimo_run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen de duplicados: {str(e)}")


@router.get(
    "/duplicados/resumen/{run_id}",
    response_model=DuplicadoResumenResponse,
    summary="Resumen de una ejecución específica de duplicados",
)
def obtener_resumen_duplicados_por_run(run_id: UUID, db: Session = Depends(get_db)):
    try:
        service = AnaliticaService(db)
        return service.obtener_resumen_duplicados(run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen de duplicados {run_id}: {str(e)}")


# ====================================================================
# ENDPOINTS: ABUSO DE ADJUDICACIÓN DIRECTA
# ====================================================================

@router.post(
    "/directas/calcular",
    response_model=ProveedorDirectaResumenResponse,
    summary="Ejecutar análisis de abuso de adjudicación directa",
    description=(
        "Detecta proveedores con más contratos directos que el umbral configurado. "
        "Agrupa por proveedor, calcula porcentaje de directas, score y clasificación de riesgo. "
        "Persiste los resultados en proveedor_adjudicacion_directa."
    ),
)
def calcular_adjudicaciones_directas(
    body: AdjudicacionDirectaCalculoRequest,
    db: Session = Depends(get_db),
):
    try:
        service = AnaliticaService(db)
        return service.calcular_abuso_adjudicacion_directa(body)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular adjudicaciones directas: {str(e)}")


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
    run_id: str | None = Query(default=None, description="UUID de la ejecución. Default: última."),
    riesgo: str | None = Query(default=None, description="Filtrar por riesgo: ALTO, MEDIO, BAJO."),
    score_minimo: float | None = Query(default=None, ge=0, description="Score mínimo."),
    score_maximo: float | None = Query(default=None, ge=0, description="Score máximo."),
    porcentaje_minimo: float | None = Query(default=None, ge=0, le=100, description="Porcentaje mínimo de directas."),
    porcentaje_maximo: float | None = Query(default=None, ge=0, le=100, description="Porcentaje máximo de directas."),
    solo_abuso_directas: bool = Query(default=False, description="True = solo ALTO y MEDIO."),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        filtros = AdjudicacionDirectaFiltroRequest(
            run_id=run_id,
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
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar adjudicaciones directas: {str(e)}")


@router.get(
    "/directas/resumen",
    response_model=ProveedorDirectaResumenResponse,
    summary="Resumen de la última ejecución de adjudicaciones directas (dashboard)",
)
def obtener_resumen_directas_ultimo(db: Session = Depends(get_db)):
    try:
        service = AnaliticaService(db)
        ultimo_run_id = service.repo.obtener_ultimo_run_id_directas()
        if not ultimo_run_id:
            raise ValueError("No existe ninguna ejecución de adjudicaciones directas registrada.")
        return service.obtener_resumen_directas(ultimo_run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen de directas: {str(e)}")


@router.get(
    "/directas/resumen/{run_id}",
    response_model=ProveedorDirectaResumenResponse,
    summary="Resumen de una ejecución específica de adjudicaciones directas",
)
def obtener_resumen_directas_por_run(run_id: UUID, db: Session = Depends(get_db)):
    try:
        service = AnaliticaService(db)
        return service.obtener_resumen_directas(run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen de directas {run_id}: {str(e)}")


# ====================================================================
# ENDPOINTS: CONFIGURACIÓN DE PESOS
# ====================================================================

@router.get(
    "/pesos",
    response_model=list[PesoAnomaliaResponse],
    summary="Obtener pesos de anomalías",
    description="Devuelve la configuración actual de pesos para el cálculo de riesgo combinado.",
)
def obtener_pesos(db: Session = Depends(get_db)):
    try:
        service = AnaliticaService(db)
        return service.obtener_pesos()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener pesos: {str(e)}")

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
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar peso: {str(e)}")


# ====================================================================
# ENDPOINTS: RIESGO COMBINADO POR PROVEEDOR
# ====================================================================

@router.post(
    "/riesgo/calcular",
    response_model=RiesgoGlobalResumenResponse,
    summary="Ejecutar cálculo de riesgo global combinado",
    description=(
        "Cruza los scores más recientes de outliers, duplicados y adjudicación directa. "
        "Aplica los pesos configurados y clasifica el riesgo del proveedor."
    ),
)
def calcular_riesgo_global(db: Session = Depends(get_db)):
    try:
        service = AnaliticaService(db)
        return service.calcular_riesgo_global()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular riesgo global: {str(e)}")

@router.get(
    "/riesgo",
    response_model=RiesgoProveedorListaResponse,
    summary="Listar proveedores con riesgo combinado",
    description="Retorna el listado de proveedores evaluados con sus scores combinados.",
)
def listar_riesgos(
    run_id: str | None = Query(default=None, description="UUID de la ejecución. Default: última."),
    proveedor: str | None = Query(default=None, description="Filtrar por nombre de proveedor."),
    riesgo: str | None = Query(default=None, description="Filtrar por riesgo: ALTO, MEDIO, BAJO."),
    score_minimo: float | None = Query(default=None, ge=0, description="Score final mínimo."),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        filtros = RiesgoFiltroRequest(
            run_id=run_id,
            proveedor=proveedor,
            riesgo=riesgo,
            score_minimo=score_minimo,
            page=page,
            page_size=page_size,
        )
        service = AnaliticaService(db)
        return service.listar_riesgos(filtros)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar riesgos: {str(e)}")

@router.get(
    "/riesgo/resumen",
    response_model=RiesgoGlobalResumenResponse,
    summary="Resumen de la última ejecución de riesgo global",
)
def obtener_resumen_riesgo_ultimo(db: Session = Depends(get_db)):
    try:
        service = AnaliticaService(db)
        ultimo_run_id = service.repo.obtener_ultimo_run_id_riesgo()
        if not ultimo_run_id:
            raise ValueError("No existe ninguna ejecución de riesgo registrada.")
        return service.obtener_resumen_riesgo(ultimo_run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen de riesgo: {str(e)}")
