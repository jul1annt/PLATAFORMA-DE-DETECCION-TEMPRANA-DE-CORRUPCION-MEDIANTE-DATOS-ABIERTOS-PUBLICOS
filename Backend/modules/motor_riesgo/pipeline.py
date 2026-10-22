"""Durable daily pipeline. No model is trained or approved by the scheduler."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import shutil
import uuid
from sqlalchemy import text
from modules.jobs.model import BackgroundJob
from modules.jobs.service import enqueue_job
from modules.ingesta.model.FuenteDatos import FuenteDatos
from .domain import STAGES
from .models import RiskCut, RiskPublication
from .service import checked_models, managed_path, publish
from core.config import settings
from .feature_store import export_observations


def due_day(now=None) -> str:
    local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo('America/Bogota'))
    if local.hour < 3:
        local -= timedelta(days=1)
    return local.date().isoformat()


def enqueue_daily(db, manual=False):
    publication = db.query(RiskPublication).filter_by(id=1).with_for_update().one()
    checked_models(db, publication.model_ids)
    from .publication import require_ready_snapshot
    require_ready_snapshot(db)
    day = due_day()
    pending = db.query(RiskCut).filter(RiskCut.status == 'PREPARANDO').order_by(RiskCut.created_at).first()
    if not manual and (not publication.daily_enabled or (publication.last_success_day == day and pending is None)):
        db.rollback()
        return None
    sources = db.query(FuenteDatos).filter(FuenteDatos.activo.is_(True)).order_by(FuenteDatos.id).all()
    sources = [s.id for s in sources if s.endpoint.endswith('/p6dx-8zbt.json')]
    if not sources:
        raise ValueError('Activar explícitamente una fuente SECOP II antes de la actualización diaria')
    # A stable key prevents overlap across manual runs, days and scheduler processes.
    job_payload = dict(pending.context) if pending else {'day': day, 'source_ids': sources, 'model_ids': dict(publication.model_ids)}
    if pending:
        job_payload['cut_id'] = str(pending.id)
    job, created = enqueue_job(db, kind='RIESGO_ACTUALIZAR', payload=job_payload, resource_key='riesgo:actualizacion')
    publication = db.query(RiskPublication).filter_by(id=1).with_for_update().one()
    if created:
        publication.last_attempt_day = day
    db.commit()
    return job


def scheduled_tick():
    from core.database import SessionLocal
    from sqlalchemy import inspect
    import logging
    with SessionLocal() as db:
        # Old deployment/schema may remain active until the migration is approved.
        if not inspect(db.get_bind()).has_table('riesgo_publicacion'):
            return
        publication = db.get(RiskPublication, 1)
        if not publication or not publication.daily_enabled:
            return
        try:
            enqueue_daily(db)
        except ValueError as exc:
            db.rollback()
            logging.getLogger(__name__).warning('Actualización analítica pendiente: %s', exc)


def signature(db) -> dict:
    rows = db.execute(text('SELECT table_name,epoch,revision,row_count FROM riesgo_versiones_datos ORDER BY table_name')).mappings().all()
    versions = {r['table_name']: r for r in rows}
    if set(versions) != {'raw_secop', 'contratos_procesados'}:
        raise ValueError('Control transaccional de la fuente ausente; aplicar y validar la migración')
    return {'rows': versions['raw_secop']['row_count'], 'normalized_rows': versions['contratos_procesados']['row_count'],
            'revisions': {name: [str(row['epoch']), row['revision']] for name, row in versions.items()}}


def update_job(db, job_id, public_id, payload):
    cut_id = uuid.UUID(payload['cut_id']) if payload.get('cut_id') else uuid.uuid5(public_id, 'risk-cut')
    cut = db.get(RiskCut, cut_id)
    if cut and cut.status == 'PUBLICADO':
        return {'cut_id': str(cut_id), 'status': 'PUBLICADO', 'resumed': True}
    checked_models(db, payload['model_ids'])
    from .publication import require_ready_snapshot
    require_ready_snapshot(db)
    disk_root = managed_path('.')
    disk_root.mkdir(parents=True, exist_ok=True)
    estimated_rows = signature(db)['rows']
    # Preserve the accepted 25 GiB reserve and budget both file/DB outputs.
    if shutil.disk_usage(disk_root).free < 25 * 1024**3 + estimated_rows * 4096:
        raise ValueError('Espacio insuficiente para preparar el corte sin afectar la reserva; revisar conservación, sin borrar datos automáticamente')
    if cut is None:
        pointer = db.get(RiskPublication, 1)
        cut = RiskCut(id=cut_id, status='PREPARANDO', context={**payload, 'step': 'INGESTA',
                      'previous_cut': str(pointer.cut_id) if pointer.cut_id else None, 'source_index': 0})
        db.add(cut)
        db.commit()
    directory = managed_path('runs/' + str(cut_id))
    directory.mkdir(parents=True, exist_ok=True)
    def progress(**changes):
        nonlocal cut
        cut = db.get(RiskCut, cut_id)
        cut.context = {**cut.context, **changes}
        db.commit()
    def blocked(reason):
        cut.status = 'BLOQUEADO'
        pointer = db.get(RiskPublication, 1)
        pointer.daily_enabled = False
        db.commit()
        return {'cut_id': str(cut_id), 'blocked': reason, 'daily_paused': True}
    if cut.context['step'] == 'INGESTA':
        for index in range(cut.context['source_index'], len(payload['source_ids'])):
            source = db.get(FuenteDatos, payload['source_ids'][index])
            if not source or not source.activo or not source.endpoint.endswith('/p6dx-8zbt.json'):
                raise ValueError('Fuente suspendida o distinta: conservar el corte anterior')
            child_id = cut.context.get('child_id')
            child = db.get(BackgroundJob, child_id) if child_id else None
            if child and child.active:
                return {'cut_id': str(cut_id), 'waiting_for': str(child.public_id)}
            if child and child.status == 'ERROR':
                return blocked('Error de ingesta; revisar y reanudar explícitamente.')
            result = child.result or {} if child else {}
            if result.get('source_paused') or result.get('replacement_detected') or result.get('source_changed'):
                return blocked('Cambio de generación; preparar carga aislada.')
            if child is None or result.get('parcial'):
                if child and not result.get('checkpoint'):
                    raise ValueError('Sincronización parcial sin cursor reanudable')
                child, _ = enqueue_job(db, kind='INGESTA', payload={'fuente_id': source.id}, resource_key=f'ingesta:{source.id}')
                progress(child_id=child.id)
                return {'cut_id': str(cut_id), 'waiting_for': str(child.public_id)}
            progress(source_index=index + 1)
            progress(child_id=None)
        progress(step='NORMALIZACION', child_id=None)
    if cut.context['step'] == 'NORMALIZACION':
        child_id = cut.context.get('child_id')
        child = db.get(BackgroundJob, child_id) if child_id else None
        if child is None:
            child, _ = enqueue_job(db, kind='REPROCESAMIENTO', payload={'forzar_reproceso': False}, resource_key='transformacion:global')
            progress(child_id=child.id)
            return {'cut_id': str(cut_id), 'waiting_for': str(child.public_id)}
        if child.active:
            return {'cut_id': str(cut_id), 'waiting_for': str(child.public_id)}
        if child.status != 'EXITOSO':
            return blocked('Normalización fallida; conservar corte anterior.')
        progress(step='VARIABLES', child_id=None)
    observations = directory / 'observations.jsonl.gz'
    if cut.context['step'] == 'VARIABLES':
        from .publication import checkpoint
        citizen_revision = checkpoint(db)
        before = signature(db)
        at = datetime.now(timezone.utc).isoformat()
        db.commit()  # release brief write fence before preparing features
        from .public_aggregates import prepare_aggregates
        citizen_aggregates=prepare_aggregates(db,citizen_revision)
        counts = export_observations(db, observations, payload['source_ids'], at)
        after = signature(db)
        if before != after:
            return blocked('La fuente cambió durante la captura; revisar y preparar un corte nuevo.')
        coverage = json.loads(observations.with_suffix('.coverage.json').read_text(encoding='utf-8'))
        if coverage['raw_rows_read'] != coverage['source_rows'] or coverage['not_normalized_rows']:
            raise ValueError('Captura o normalización incompleta; conservar el corte anterior')
        progress(step='INFERENCIA', signature=before, counts=counts, data_cut_at=at,citizen_revision=citizen_revision,
                 citizen_aggregates=citizen_aggregates,
                 capture_coverage=coverage,
                 observations_sha256=coverage['observations_sha256'])
    models = checked_models(db, payload['model_ids'])
    if cut.context['step'] == 'INFERENCIA':
        from .publication import checkpoint
        if signature(db)!=cut.context['signature'] or checkpoint(db)!=cut.context['citizen_revision']:
            return blocked('Los datos cambiaron antes de inferir; conservar el corte anterior y preparar uno nuevo.')
        db.commit()  # release the brief checkpoint fence before external work
        from .inference_artifact import completed_inference
        from .result_store import persist_results
        artifacts = {stage: model.artifact for stage, model in models.items()}
        try:
            output,manifest=completed_inference(directory,observations,cut.context,artifacts,settings.RISK_INFERENCE_PYTHON)
        except (ValueError,OSError,KeyError,TypeError) as exc:
            db.rollback();cut=db.get(RiskCut,cut_id)
            return blocked('Artefacto de inferencia no verificable: '+type(exc).__name__)
        if sum(manifest['evaluated_counts'].values())==0:
            progress(inference_manifest=manifest)
            return blocked('Sin operaciones con evidencia temporal evaluable; conservar el corte anterior.')
        try:
            persist_results(db,cut_id,output,manifest)
        except ValueError as exc:
            db.rollback();cut=db.get(RiskCut,cut_id)
            return blocked(str(exc))
        progress(inference_manifest=manifest)
        if signature(db) != cut.context['signature']:
            return blocked('Los datos cambiaron durante inferencia; conservar el corte anterior y preparar uno nuevo.')
        progress(step='PUBLICACION')
        cut.status = 'VALIDADO'
        db.commit()
    try:
        publish(db, cut_id)
    except ValueError as exc:
        # A stale validated candidate must not be re-enqueued forever by the
        # scheduler. Preserve the preceding pointers and require explicit review.
        db.rollback()
        cut=db.get(RiskCut,cut_id)
        return blocked(str(exc))
    return {'cut_id': str(cut_id), 'status': 'PUBLICADO', 'counts': cut.context['counts']}
