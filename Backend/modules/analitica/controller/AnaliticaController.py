from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.dependencies import get_db
from modules.analitica.dto.request import OutlierCalculoRequest, OutlierFiltroRequest
from modules.analitica.dto.response import RunResumenResponse, OutlierListaResponse
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