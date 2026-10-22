"""Public revisions span contracts, quality findings, metrics and risk results.

Before images preserve only changed rows. A fixed revision remains readable
while ordinary ingestion and normalization continue in their own transactions.
"""
from contextlib import contextmanager
from uuid import UUID, uuid4, uuid5
from sqlalchemy import event, text
from .models import CitizenSnapshot, CitizenPublication, RiskCut

TABLES = ('contratos_procesados','contrato_anomalo_incompleto',
          'contratos_metricas_calidad','estadistica_campos_faltantes')


class SnapshotNotFound(ValueError):
    pass


def checkpoint(db) -> int:
    # Including all four tables waits for in-flight writers, even if sequence
    # allocation and transaction commit happened in different orders. SELECTs
    # remain available. Writers after this fence receive greater revisions.
    db.execute(text("SET LOCAL lock_timeout='2s'"))
    db.execute(text('LOCK TABLE '+','.join('public.'+table for table in TABLES)+' IN SHARE MODE'))
    value, called = db.execute(text('SELECT last_value,is_called FROM public.riesgo_revision_ciudadana')).one()
    return int(value) if called else 0


def initialize_baseline(db, data_cut_at: str, *, compute_aggregates=True, snapshot_id=None):
    pointer = db.get(CitizenPublication,1)
    if pointer:
        snapshot=db.get(CitizenSnapshot,pointer.snapshot_id)
    else:
        snapshot=db.get(CitizenSnapshot,snapshot_id) if snapshot_id else None
        if snapshot is None:
            revision = checkpoint(db)
            snapshot = CitizenSnapshot(id=snapshot_id or uuid4(),revision=revision,risk_cut_id=None,data_cut_at=data_cut_at)
            db.add(snapshot);db.flush()
        elif snapshot.risk_cut_id is not None or snapshot.data_cut_at!=data_cut_at:
            raise ValueError('La base preparada no corresponde al trabajo solicitado')
    if compute_aggregates:
        from .public_aggregates import prepare_aggregates,validate_aggregates
        if snapshot.aggregates is None:
            snapshot.aggregates=prepare_aggregates(db,snapshot.revision);db.flush()
        else:validate_aggregates(snapshot.aggregates,snapshot.revision)
        if pointer is None:
            db.add(CitizenPublication(id=1,snapshot_id=snapshot.id));db.flush()
    return snapshot


def prepare_baseline_job(db,job_public_id=None):
    from core.config import settings
    identifier=uuid5(UUID(str(job_public_id)),'citizen-baseline') if job_public_id else uuid4()
    snapshot=initialize_baseline(db,settings.RISK_BASELINE_CUT_DATE.isoformat(),compute_aggregates=False,snapshot_id=identifier)
    identifier=snapshot.id
    db.commit()  # release initial write fence; subsequent reads use this revision
    snapshot=initialize_baseline(db,settings.RISK_BASELINE_CUT_DATE.isoformat(),snapshot_id=identifier)
    db.commit()
    return {'public_cut_id':str(identifier),'aggregates_ready':True,'data_cut_at':snapshot.data_cut_at}


def require_ready_snapshot(db):
    from .public_aggregates import validate_aggregates
    pointer=db.get(CitizenPublication,1)
    if pointer is None:
        raise ValueError('Preparar primero la base ciudadana mediante el trabajo administrativo')
    snapshot=db.get(CitizenSnapshot,pointer.snapshot_id)
    if snapshot is None:raise ValueError('Falta el corte ciudadano conservado')
    validate_aggregates(snapshot.aggregates,snapshot.revision)
    return snapshot


def activate_snapshot(db, cut):
    revision = cut.context.get('citizen_revision')
    if type(revision) is not int or revision<0 or checkpoint(db)!=revision:
        raise ValueError('Los datos ciudadanos cambiaron o no tienen una revisión completa')
    pointer = db.query(CitizenPublication).filter_by(id=1).with_for_update().one_or_none()
    if pointer is None:
        raise ValueError('Congelar el corte ciudadano de base antes de iniciar la ingesta')
    from .public_aggregates import validate_aggregates
    aggregates=validate_aggregates(cut.context.get('citizen_aggregates'),revision)
    if cut.context.get('signature') and aggregates['rows']!=cut.context['signature']['normalized_rows']:
        raise ValueError('Los agregados no cubren todos los contratos normalizados')
    snapshot = db.get(CitizenSnapshot,cut.id)
    if snapshot is None:
        snapshot = CitizenSnapshot(id=cut.id,revision=revision,risk_cut_id=cut.id,data_cut_at=cut.context['data_cut_at'],aggregates=aggregates)
        db.add(snapshot);db.flush()
    elif snapshot.revision != revision or snapshot.risk_cut_id != cut.id or snapshot.aggregates!=aggregates:
        raise ValueError('La revisión ciudadana no corresponde al corte')
    pointer.snapshot_id = snapshot.id


def restore_snapshot(db, cut_id):
    snapshot=db.get(CitizenSnapshot,cut_id)
    if snapshot is None or snapshot.risk_cut_id!=cut_id:
        raise ValueError('El corte no conserva una revisión ciudadana')
    from .public_aggregates import validate_aggregates
    validate_aggregates(snapshot.aggregates,snapshot.revision)
    pointer=db.query(CitizenPublication).filter_by(id=1).with_for_update().one()
    pointer.snapshot_id=snapshot.id


def select_snapshot(db, selected: UUID | None = None):
    if db.get_bind().dialect.name!='postgresql':
        return None
    exists = db.execute(text("SELECT to_regclass('public.riesgo_publicacion_ciudadana') IS NOT NULL")).scalar_one()
    if not exists:
        if selected: raise SnapshotNotFound('El corte ciudadano solicitado no está disponible')
        return None
    pointer = db.get(CitizenPublication,1)
    if not pointer:
        if selected: raise SnapshotNotFound('El corte ciudadano solicitado no está disponible')
        return None
    snapshot = db.get(CitizenSnapshot,selected or pointer.snapshot_id)
    if snapshot is None:
        raise SnapshotNotFound('El corte ciudadano solicitado no está disponible')
    if snapshot.risk_cut_id:
        cut=db.get(RiskCut,snapshot.risk_cut_id)
        if cut is None or cut.status!='PUBLICADO':
            raise SnapshotNotFound('El corte ciudadano solicitado no está publicado')
    return {'id':str(snapshot.id),'revision':snapshot.revision,
            'risk_cut_id':str(snapshot.risk_cut_id) if snapshot.risk_cut_id else None,'data_cut_at':snapshot.data_cut_at,
            'explicit':selected is not None,'aggregates':snapshot.aggregates}


@contextmanager
def read_snapshot(db, selected: UUID | None = None):
    snapshot=select_snapshot(db,selected)
    with revision_scope(db,snapshot):
        yield snapshot


@contextmanager
def revision_scope(db,snapshot):
    if snapshot is None:
        yield None
        return
    # The normal HTTP session has an empty identity map. The listener also
    # protects callers that previously loaded mutable entities in this session.
    def populate(query):
        if query.is_select:
            query.update_execution_options(populate_existing=True)
    nested=db.begin_nested()
    previous=db.info.get('public_snapshot')
    listening=False
    try:
        db.execute(text("SELECT set_config('riesgo.public_revision',:revision,true),set_config('search_path','riesgo_ciudadano,public',true)"),{'revision':str(snapshot['revision'])})
        db.info['public_snapshot']=snapshot
        event.listen(db,'do_orm_execute',populate)
        listening=True
        yield snapshot
    finally:
        if listening: event.remove(db,'do_orm_execute',populate)
        if nested.is_active: nested.rollback()
        if previous is None: db.info.pop('public_snapshot',None)
        else: db.info['public_snapshot']=previous
        db.expire_all()
