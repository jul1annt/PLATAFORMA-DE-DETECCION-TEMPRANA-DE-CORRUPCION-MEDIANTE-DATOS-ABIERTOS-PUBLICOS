from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from core.database import get_db
from core.public_database import get_public_db
from gateway.middlewares.auth_middleware import get_current_admin
from modules.auth.dto.response import AdminResponse
from modules.jobs.service import enqueue_job, to_job_accepted
from modules.jobs.dto import BackgroundJobAccepted
from .domain import REFERENCES, FEATURE_VERSION
from .models import JudicialCase, RiskResult, RiskPublication, RiskModel, RiskCut, RiskFeatureEvidence
from .service import register_case, activate, status, audit, checked_published_models

router = APIRouter(prefix='/riesgo', tags=['Motor de riesgo'])


class CaseRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    record: dict


class TrainRequest(BaseModel):
    dataset: str = Field(min_length=1, max_length=240, pattern=r'^[a-zA-Z0-9_./-]+\.jsonl(?:\.gz)?$')


class ActivationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    convocatoria: UUID
    adjudicacion: UUID
    daily: bool = True


class RiskStatusResponse(BaseModel):
    available: bool
    cut_id: str | None
    data_cut_at: str | None
    public_cut_id: str | None = None
    public_data_cut_at: str | None = None
    daily_enabled: bool
    last_attempt_day: str | None
    last_success_day: str | None
    update_status: str
    message: str


class ResultResponse(BaseModel):
    raw_secop_id: int
    stage: str
    result: dict


class PageResponse(BaseModel):
    items: list[ResultResponse]
    total: int
    cut_id: str | None


@router.get('/estado', response_model=RiskStatusResponse)
def get_status(db: Session = Depends(get_public_db)):
    return status(db)


@router.get('/metodologia')
def methodology():
    from .catalog import INDICATORS, development_reference
    return {'feature_version': FEATURE_VERSION, 'stages': ['CONVOCATORIA', 'ADJUDICACION'],
            'references': REFERENCES, 'indicators': INDICATORS, 'index': 'Percentil de prioridad sobre referencia congelada por versión y etapa.',
            'limits': ['Una alerta no acredita corrupción.', 'Los registros sin etiqueta no son negativos.',
                       'La calidad del dato se muestra separada del riesgo.', 'Los índices de etapas distintas no son comparables.'],
            'publication_gate': 'Los dos modelos deben superar evaluación temporal independiente y por proveedores no vistos.',
            'index_scope': 'Modelos aprobados por etapa; no el conteo de familias de la referencia.',
            'development_reference': development_reference()}


@router.get('/resultados', response_model=PageResponse)
def results(stage: Literal['CONVOCATORIA', 'ADJUDICACION'] | None = None,
            raw_secop_id: int | None = Query(None, ge=1), offset: int = Query(0, ge=0),
            raw_secop_ids: list[int] | None = Query(None, max_length=200),
            cut_id: UUID | None = None,
            limit: int = Query(25, ge=1, le=200), db: Session = Depends(get_public_db)):
    publication = db.get(RiskPublication, 1)
    snapshot=db.info.get('public_snapshot')
    snapshot_cut=snapshot['risk_cut_id'] if snapshot else None
    if cut_id and snapshot and snapshot['explicit'] and str(cut_id)!=snapshot_cut:
        raise HTTPException(409,'Los datos ciudadanos y el índice deben pertenecer al mismo corte.')
    selected_id = cut_id or (snapshot_cut if snapshot else (publication.cut_id if publication else None))
    if not selected_id:
        return {'items': [], 'total': 0, 'cut_id': None}
    cut = db.get(RiskCut, selected_id)
    if not cut or cut.status != 'PUBLICADO':
        raise HTTPException(404, 'El corte solicitado no tiene publicación validada.')
    query = db.query(RiskResult).filter_by(cut_id=selected_id)
    if stage:
        query = query.filter_by(stage=stage)
    if raw_secop_id:
        query = query.filter_by(raw_secop_id=raw_secop_id)
    if raw_secop_ids is not None:
        query = query.filter(RiskResult.raw_secop_id.in_(raw_secop_ids))
    # Full counts were validated at the atomic publication. Avoid counting
    # millions of results again for every public page; filtered IDs stay small.
    counts = cut.context.get('counts', {})
    total = query.count() if raw_secop_id or raw_secop_ids is not None else (counts.get(stage, 0) if stage else sum(counts.values()))
    rows = query.order_by(RiskResult.raw_secop_id, RiskResult.stage).offset(offset).limit(limit).all()
    return {'items': [{'raw_secop_id': r.raw_secop_id, 'stage': r.stage, 'result': r.result} for r in rows],
            'total': total, 'cut_id': str(selected_id)}


@router.post('/admin/casos')
def add_case(request: CaseRequest, admin: AdminResponse = Depends(get_current_admin), db: Session = Depends(get_db)):
    try:
        if not isinstance(request.record.get('case_id'), str) or not 1 <= len(request.record['case_id']) <= 100:
            raise ValueError('case_id requerido (1–100 caracteres)')
        return register_case(db, request.record, admin.id)
    except (ValueError, KeyError, TypeError):
        db.rollback()
        raise HTTPException(422, 'Registro de caso inválido o ya existente; comprobar evidencia y campos requeridos.') from None


@router.get('/admin/inventario', dependencies=[Depends(get_current_admin)])
def inventory(db: Session = Depends(get_db)):
    rows = db.query(JudicialCase).order_by(JudicialCase.case_id).all()
    return {'candidates': len(rows), 'eligible_cases': sum(r.eligible for r in rows),
            'cases': [{'case_id': r.case_id, 'eligible': r.eligible, 'exclusions': r.exclusions,
                       'sha256': r.record_sha256} for r in rows]}


@router.get('/admin/modelos', dependencies=[Depends(get_current_admin)])
def models(db: Session = Depends(get_db)):
    return [{'id': str(m.id), 'stage': m.stage, 'version': m.version, 'validated': m.validated, 'report': m.report}
            for m in db.query(RiskModel).order_by(RiskModel.created_at.desc()).limit(100)]


@router.post('/admin/evidencias-variables')
def add_feature_evidence(request: CaseRequest, admin: AdminResponse = Depends(get_current_admin), db: Session = Depends(get_db)):
    from .service import register_feature_evidence
    try:
        return register_feature_evidence(db, request.record, admin.id)
    except (ValueError, KeyError, TypeError, OSError, OverflowError):
        db.rollback()
        raise HTTPException(422, 'Revisión inválida: comprobar documentos físicos, fechas, valores, etapa e identidad SECOP.') from None


@router.get('/admin/evidencias-variables', dependencies=[Depends(get_current_admin)])
def feature_evidence(offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=200), db: Session = Depends(get_db)):
    query = db.query(RiskFeatureEvidence)
    return {'total': query.count(), 'items': [{'evidence_id': row.evidence_id, 'record_sha256': row.record_sha256,
             'registered_by': row.registered_by, 'created_at': row.created_at}
            for row in query.order_by(RiskFeatureEvidence.evidence_id).offset(offset).limit(limit)]}


@router.post('/admin/entrenar', response_model=BackgroundJobAccepted)
def train(request: TrainRequest, admin: AdminResponse = Depends(get_current_admin), db: Session = Depends(get_db)):
    from .service import managed_path
    try:
        if not managed_path(request.dataset).is_file():
            raise ValueError('Conjunto ausente')
    except ValueError:
        raise HTTPException(422, 'El conjunto debe existir en el directorio analítico administrado.') from None
    job, _ = enqueue_job(db, kind='RIESGO_ENTRENAR', payload={'dataset': request.dataset, 'admin_id': admin.id}, resource_key='riesgo:entrenar')
    return to_job_accepted(job)


@router.post('/admin/activar')
def activation(request: ActivationRequest, admin: AdminResponse = Depends(get_current_admin), db: Session = Depends(get_db)):
    try:
        return activate(db, {'CONVOCATORIA': str(request.convocatoria), 'ADJUDICACION': str(request.adjudicacion)}, admin.id, request.daily)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from None


@router.post('/admin/preparar-base',response_model=BackgroundJobAccepted,status_code=202)
def prepare_public_base(admin: AdminResponse=Depends(get_current_admin),db: Session=Depends(get_db)):
    job,_=enqueue_job(db,kind='RIESGO_BASE_CIUDADANA',payload={'admin_id':admin.id},resource_key='riesgo:base-ciudadana')
    return to_job_accepted(job)


@router.post('/admin/actualizar', response_model=BackgroundJobAccepted)
def refresh(admin: AdminResponse = Depends(get_current_admin), db: Session = Depends(get_db)):
    from .pipeline import enqueue_daily
    try:
        return to_job_accepted(enqueue_daily(db, manual=True))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from None


@router.post('/admin/revertir/{cut_id}')
def revert(cut_id: UUID, admin: AdminResponse = Depends(get_current_admin), db: Session = Depends(get_db)):
    pointer = db.query(RiskPublication).filter_by(id=1).with_for_update().one()
    cut = db.get(RiskCut, cut_id)
    if not cut or cut.status != 'PUBLICADO':
        raise HTTPException(409, 'Solo puede restaurarse un corte previamente publicado.')
    from .publication import restore_snapshot
    try:
        checked_published_models(db, cut)
        restore_snapshot(db,cut_id)
    except (ValueError,KeyError,TypeError):
        db.rollback()
        raise HTTPException(409, 'El corte no conserva modelos, aprobación y datos ciudadanos íntegros.') from None
    previous = str(pointer.cut_id)
    pointer.cut_id, pointer.model_ids, pointer.daily_enabled = cut.id, cut.context['model_ids'], False
    audit(db, 'REVERTIR', str(admin.id), {'cut_id': str(cut_id), 'previous_cut': previous, 'daily_paused': True})
    db.commit()
    return status(db)
