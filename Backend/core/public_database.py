"""Request-local citizen snapshot binding; administrative writes stay separate."""
from uuid import UUID
from fastapi import Depends, Header, HTTPException, Response, Request
from fastapi.dependencies.utils import request_params_to_args
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from core.database import get_db
from core.read_database import apply_read_parallelism
from core.config import settings
from modules.motor_riesgo.publication import read_snapshot, SnapshotNotFound
from modules.motor_riesgo.public_aggregates import AggregatesNotReady


def validate_before_binding(request: Request):
    """Preserve the existing rejection of invalid requests before DB access."""
    route=request.scope['route']
    if route.endpoint.__name__=='exportar_contratos':
        from modules.transformacion.controller.transformacionController import _parse_export_filters
        if request.path_params.get('formato') not in {'csv','xlsx','pdf'}:
            raise HTTPException(422,'Formato de exportación inválido')
        _parse_export_filters(request)
        return
    from shared.request_validation import reject_unknown_query_params
    reject_unknown_query_params(request,{field.alias for field in route.dependant.query_params})
    values,errors=request_params_to_args(route.dependant.query_params,request.query_params)
    _,path_errors=request_params_to_args(route.dependant.path_params,request.path_params)
    if errors or path_errors:
        raise RequestValidationError(errors+path_errors)
    if route.endpoint.__name__=='search_procesados':
        for lower,upper in (('fecha_inicio','fecha_fin'),('valor_min','valor_max'),('nivel_confianza_min','nivel_confianza_max')):
            if values.get(lower) is not None and values.get(upper) is not None and values[lower]>values[upper]:
                raise HTTPException(400,lower+' no puede ser mayor que '+upper)


def get_public_db(request: Request,response: Response, x_public_cut: UUID | None = Header(None), db: Session = Depends(get_db)):
    validate_before_binding(request)
    if x_public_cut is None and request.scope['route'].endpoint.__name__=='results' and request.query_params.get('cut_id'):
        x_public_cut=UUID(request.query_params['cut_id'])
    try:
        with read_snapshot(db,x_public_cut) as snapshot:
            if snapshot:
                response.headers['X-Public-Cut']=snapshot['id']
                response.headers['X-Data-Cut-At']=snapshot['data_cut_at']
            yield db
    except SnapshotNotFound as exc:
        raise HTTPException(404,'El corte ciudadano solicitado no está disponible.') from exc
    except AggregatesNotReady as exc:
        raise HTTPException(503,'El tablero de este corte se está preparando. Inténtalo nuevamente.') from exc


def get_public_search_db(db: Session=Depends(get_public_db)):
    return apply_read_parallelism(db,settings.SEARCH_QUERY_PARALLEL_WORKERS)


def get_public_provider_db(db: Session=Depends(get_public_db)):
    return apply_read_parallelism(db,settings.PROVIDER_QUERY_PARALLEL_WORKERS)
