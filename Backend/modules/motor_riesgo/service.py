"""Administrative orchestration; heavy computation is delegated to isolated Python."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib
import os
import subprocess
import uuid
from sqlalchemy import text, func
from core.config import settings
from .domain import STAGES, digest, eligible_case
from .models import JudicialCase, RiskAudit, RiskModel, RiskCut, RiskResult, RiskPublication, RiskFeatureEvidence


def work_root() -> Path:
    return Path(settings.RISK_WORK_DIR).resolve()


def managed_path(relative: str) -> Path:
    root = work_root()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('La ruta debe permanecer en el directorio analítico')
    return path


def audit(db, action: str, actor: str, detail: dict):
    db.add(RiskAudit(action=action, actor=actor, detail=detail))


def run_process(interpreter: str, args: list[str], timeout=14400):
    executable = Path(interpreter)
    if not executable.is_absolute() or not executable.is_file():
        raise ValueError('Configurar el intérprete aislado antes de ejecutar modelos')
    environment = {k: v for k, v in os.environ.items() if not k.startswith(('DB_', 'SECRET_', 'ENCRYPTION_'))}
    environment.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONHASHSEED='0', PYTHONNOUSERSITE='1',PYTHONIOENCODING='utf-8')
    log = Path(args[args.index('--output') + 1]).with_suffix('.process.log')
    if not log.resolve().is_relative_to(work_root()):
        raise ValueError('Registro de ejecución fuera del directorio analítico')
    from .process_runner import bounded_run
    receipt=log.with_suffix('.execution.json')
    execution={'scope':'execution_lifecycle_not_predictive_approval','started_at':datetime.now(timezone.utc).isoformat(),
               'status':'RUNNING','maximum_seconds':timeout,'thread_limits':{name:environment[name] for name in
               ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')},
               'venv_executable':str(executable),'venv_executable_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
               'launcher_code_sha256':{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                       for name in ('service.py','process_runner.py','windows_job.py')}}
    def finish(status):
        execution.update(status=status,finished_at=datetime.now(timezone.utc).isoformat())
        receipt.write_text(json.dumps(execution,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    receipt.write_text(json.dumps(execution,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    try:
        result = bounded_run([str(executable), '-I', str(Path(__file__).resolve().parents[2] / 'scripts' / 'risk_process.py'), *args],
                             cwd=Path(__file__).resolve().parents[2], env=environment, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        finish('TIMEOUT_TREE_CLOSED')
        log.write_text((exc.output or '')+(exc.stderr or '')+'\nTiempo máximo agotado; árbol analítico cerrado.\n',encoding='utf-8')
        raise
    except RuntimeError as exc:
        finish('PROCESS_CONTROL_FAILED')
        log.write_text('Fallo de control del proceso analítico: '+str(exc)+'\n',encoding='utf-8')
        raise
    except BaseException as exc:
        finish('INTERRUPTED_OR_LAUNCH_FAILED')
        log.write_text('Inicio o interrupción del proceso analítico: '+type(exc).__name__+'\n',encoding='utf-8')
        raise
    execution['returncode']=result.returncode
    finish('COMPLETED' if result.returncode==0 else 'FAILED_EXIT')
    log.write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError('El proceso analítico falló; revisar su entrada y dependencias (salida no publicada)')


def register_case(db, record: dict, admin_id: int) -> dict:
    from analytics_ml.corpus import verified_cases
    accepted, inventory = verified_cases([record], managed_path('evidence'))
    key = record['case_id']
    if db.get(JudicialCase, key) is not None:
        raise ValueError('El caso ya existe; registrar una revisión con un identificador nuevo')
    reasons = inventory['exclusions'][0]['reasons'] if inventory['exclusions'] else []
    from modules.ingesta.model.RawSecop import RawSecop
    for operation in record.get('operations') or []:
        query = db.query(RawSecop).filter_by(fuente_id=operation.get('source_id'),
            socrata_row_id=operation.get('source_row_id'),id_del_proceso=operation.get('process_id'))
        if operation.get('award_id'):
            query = query.filter_by(id_adjudicacion=operation['award_id'])
        if query.limit(2).count() != 1:
            reasons.append('identidad_secop_no_confirmada_en_base')
        if operation.get('lot_id'):
            reasons.append('identidad_lote_no_disponible_en_fuente')
    reasons = sorted(set(reasons))
    is_eligible = key in accepted and not reasons
    db.add(JudicialCase(case_id=key, record=record, record_sha256=digest(record), eligible=is_eligible,
                        exclusions=reasons, registered_by=admin_id))
    audit(db, 'REGISTRAR_CASO', str(admin_id), {'case_id': key, 'sha256': digest(record), 'eligible': is_eligible})
    db.commit()
    return {'case_id': key, 'eligible': is_eligible, 'exclusions': reasons}


def train_job(db, relative_dataset: str, job_public_id) -> dict:
    dataset = managed_path(relative_dataset)
    if not dataset.is_file() or dataset.stat().st_size > 512 * 1024 * 1024:
        raise ValueError('Conjunto ausente o mayor de 512 MiB')
    directory = managed_path('runs/' + str(job_public_id))
    directory.mkdir(parents=True, exist_ok=True)
    cases_file, result_file = directory / 'cases.json', directory / 'training.json'
    evidence_file = directory / 'feature-evidence.json'
    records = [{**row.record, 'registration_eligible': row.eligible} for row in db.query(JudicialCase).order_by(JudicialCase.case_id)]
    evidence = [{'record': row.record, 'record_sha256': row.record_sha256, 'registered_by': row.registered_by}
                for row in db.query(RiskFeatureEvidence).order_by(RiskFeatureEvidence.evidence_id)]
    from analytics_ml.streams import logical_sha256, physical_sha256
    frozen = {'dataset_sha256': logical_sha256(dataset, 512 * 1024**2),
              'dataset_file_sha256': physical_sha256(dataset), 'cases_sha256': digest(records), 'feature_evidence_sha256': digest(evidence)}
    manifest = directory / 'inputs.json'
    if manifest.exists() and json.loads(manifest.read_text(encoding='utf-8')) != frozen:
        raise ValueError('Los insumos cambiaron durante el entrenamiento; crear un trabajo nuevo')
    manifest.write_text(json.dumps(frozen), encoding='utf-8')
    if not result_file.exists():
        cases_file.write_text(json.dumps(records, ensure_ascii=False), encoding='utf-8')
        evidence_file.write_text(json.dumps(evidence, ensure_ascii=False), encoding='utf-8')
        run_process(settings.RISK_TRAINING_PYTHON, ['train', '--cases', str(cases_file), '--evidence', str(managed_path('evidence')),
                    '--feature-evidence', str(evidence_file),
                    '--observations', str(dataset), '--output', str(result_file), '--version', str(job_public_id)])
    output = json.loads(result_file.read_text(encoding='utf-8'))
    if output.get('inputs') != {'observations_sha256': frozen['dataset_sha256'],
                              'observations_file_sha256': frozen['dataset_file_sha256'], 'cases_sha256': frozen['cases_sha256'],
                              'feature_evidence_sha256': frozen['feature_evidence_sha256']}:
        raise ValueError('Los insumos realmente leídos no corresponden al manifiesto congelado')
    ids = {}
    for stage, item in output['stages'].items():
        if 'artifact' not in item:
            continue
        artifact, report = item['artifact'], item['report']
        from analytics_ml.inference import validate_artifact
        from analytics_ml.approval import validate_approval
        validate_artifact(artifact)
        if report.get('artifact_sha256') != artifact['sha256'] or report.get('sha256') != digest({k:v for k,v in report.items() if k != 'sha256'}):
            raise ValueError('El informe no corresponde al artefacto')
        if (artifact.get('stage') != stage or report.get('stage') != stage
                or report.get('version') != artifact.get('version')
                or type(report.get('validated')) is not bool):
            raise ValueError('Etapa, versión o estado del resultado de entrenamiento incompatibles')
        # The persisted validation flag must mean the same thing as activation
        # and startup approval, including when resuming a cached child result.
        # A failed comparison remains a candidate; an inconsistent claimed
        # approval is rejected before adding a model to the transaction.
        validated = report['validated']
        if validated:
            validate_approval(artifact, report, stage, artifact['version'], True)
        model_id = uuid.uuid5(job_public_id, stage)
        if not db.get(RiskModel, model_id):
            db.add(RiskModel(id=model_id, stage=stage, version=artifact['version'], artifact=artifact, report=report,
                validated=validated))
        ids[stage] = str(model_id)
    audit(db, 'ENTRENAR', str(job_public_id), {'models': ids, 'inventory': output['inventory']})
    db.commit()
    return {'models': ids, 'inventory': output['inventory'], 'feature_evidence': output['feature_evidence'],
            'coverage': {s:i['coverage'] for s,i in output['stages'].items()},
            'blocked': {s:i.get('reason') for s,i in output['stages'].items() if i.get('blocked')}}


def register_feature_evidence(db, record: dict, admin_id: int) -> dict:
    from analytics_ml.evidence import validate_record
    validate_record(record, managed_path('evidence'))
    key = record['evidence_id']
    if db.get(RiskFeatureEvidence, key):
        raise ValueError('La revisión ya existe; usar una nueva versión de evidencia')
    # Match against preserved source identities; never invent a legacy row ID.
    from modules.ingesta.model.RawSecop import RawSecop
    observation = record['observation']
    if type(observation.get('raw_secop_id')) is not int or observation['raw_secop_id']<1:
        raise ValueError('Identificar explícitamente la fila conservada de SECOP')
    query = db.query(RawSecop).filter_by(fuente_id=observation['source_id'],
        socrata_row_id=observation['source_row_id'], id_del_proceso=observation['process_id'])
    if observation['stage'] == 'ADJUDICACION':
        query = query.filter_by(id_adjudicacion=observation['award_id'])
    matches=query.limit(2).all()
    if observation.get('lot_id') or len(matches)!=1 or matches[0].id!=observation['raw_secop_id']:
        raise ValueError('Identidad SECOP no confirmada en la base')
    from .domain import instant
    event=matches[0].fecha_adjudicacion if observation['stage']=='ADJUDICACION' else matches[0].fecha_de_publicacion_del
    if event is None or instant(event.isoformat())!=instant(observation['prediction_at']):
        raise ValueError('La fecha revisada no coincide con la etapa conservada de SECOP')
    checksum = digest(record)
    db.add(RiskFeatureEvidence(evidence_id=key, record=record, record_sha256=checksum, registered_by=admin_id,
        raw_secop_id=observation['raw_secop_id'],stage=observation['stage'],prediction_at=instant(observation['prediction_at'])))
    audit(db, 'REGISTRAR_EVIDENCIA_VARIABLES', str(admin_id), {'evidence_id': key, 'sha256': checksum})
    db.commit()
    return {'evidence_id': key, 'record_sha256': checksum}


def checked_models(db, ids: dict) -> dict:
    from analytics_ml.approval import validate_approval
    if set(ids) != set(STAGES):
        raise ValueError('Se requieren los dos modelos validados')
    models = {}
    for stage in STAGES:
        model = db.get(RiskModel, uuid.UUID(str(ids[stage])))
        if not model or model.stage != stage or not model.validated:
            raise ValueError('Modelo no validado para la etapa ' + stage)
        validate_approval(model.artifact, model.report, stage, model.version, model.validated)
        models[stage] = model
    return models


def publication_certificate(models: dict) -> dict:
    """Freeze the approval actually checked when publishing this immutable cut."""
    return {stage: {'model_id': str(model.id), 'version': model.version,
                   'feature_version': model.artifact['feature_version'],
                   'artifact_sha256': model.artifact['sha256'], 'report_sha256': model.report['sha256']}
            for stage, model in models.items()}


def checked_published_models(db, cut) -> dict:
    """Restore persisted results without executing an obsolete feature pipeline.

    New inference still requires checked_models and the current feature version.
    A previous publication must retain its exact model and approval report.
    """
    ids = cut.context.get('model_ids', {})
    certificate = cut.context.get('approval_certificate', {})
    if set(ids) != set(STAGES) or set(certificate) != set(STAGES):
        raise ValueError('El corte no conserva la aprobación de ambos modelos')
    models = {}
    for stage in STAGES:
        model = db.get(RiskModel, uuid.UUID(str(ids[stage])))
        if model is None or not model.validated or model.stage != stage:
            raise ValueError('Modelo histórico no conservado para ' + stage)
        artifact, report = model.artifact, model.report
        if (artifact.get('sha256') != digest({k:v for k,v in artifact.items() if k != 'sha256'})
                or report.get('sha256') != digest({k:v for k,v in report.items() if k != 'sha256'})
                or report.get('artifact_sha256') != artifact.get('sha256')
                or artifact.get('stage') != stage or report.get('stage') != stage
                or artifact.get('version') != model.version or report.get('version') != model.version
                or report.get('validated') is not True):
            raise ValueError('El modelo o su informe histórico cambiaron')
        models[stage] = model
    if publication_certificate(models) != certificate:
        raise ValueError('La aprobación histórica difiere del corte publicado')
    return models


def activate(db, ids: dict, admin_id: int, daily: bool) -> dict:
    checked_models(db, ids)
    publication = db.query(RiskPublication).filter_by(id=1).with_for_update().one()
    from .publication import require_ready_snapshot
    require_ready_snapshot(db)
    publication.model_ids = ids
    publication.daily_enabled = daily
    publication.updated_at = datetime.now(timezone.utc)
    audit(db, 'APROBAR_MODELOS', str(admin_id), {'models': ids, 'daily_enabled': daily})
    db.commit()
    return {'models': ids, 'daily_enabled': daily, 'publication_pending': True}


def publish(db, cut_id, actor='worker') -> None:
    publication = db.query(RiskPublication).filter_by(id=1).with_for_update().one()
    cut = db.get(RiskCut, cut_id)
    if not cut or cut.status != 'VALIDADO' or cut.context.get('model_ids') != publication.model_ids:
        raise ValueError('Corte incompleto o modelos diferentes')
    models = checked_models(db, publication.model_ids)
    # Brief publication lock closes the check/commit race with source writes.
    # It never blocks public SELECTs and times out instead of waiting indefinitely.
    if cut.context.get('signature'):
        from .pipeline import signature
        db.execute(text("SET LOCAL lock_timeout='2s'"))
        db.execute(text('LOCK TABLE raw_secop,contratos_procesados IN SHARE MODE'))
        if signature(db) != cut.context['signature']:
            raise ValueError('El origen cambió antes de publicar')
    statistics=db.query(RiskResult.stage,func.count(),func.count(RiskResult.result['index'].astext)).filter_by(cut_id=cut_id).group_by(RiskResult.stage).all()
    counts={s:0 for s in STAGES};evaluated={s:0 for s in STAGES}
    for stage,total,scored in statistics:
        if stage not in counts:raise ValueError('Etapa de resultados inválida')
        counts[stage]=total;evaluated[stage]=scored
    if counts != cut.context.get('counts') or sum(counts.values()) == 0:
        raise ValueError('Cobertura del corte incompleta')
    if sum(evaluated.values())==0:
        raise ValueError('El corte no contiene operaciones con evidencia temporal evaluable')
    manifest=cut.context.get('inference_manifest')
    if manifest and manifest.get('evaluated_counts')!=evaluated:
        raise ValueError('La cobertura evaluable persistida difiere de la inferencia')
    from .publication import activate_snapshot
    activate_snapshot(db,cut)
    cut.context = {**cut.context, 'approval_certificate': publication_certificate(models)}
    publication.cut_id = cut.id
    publication.last_success_day = cut.context['day']
    publication.updated_at = datetime.now(timezone.utc)
    cut.status = 'PUBLICADO'
    cut.finished_at = datetime.now(timezone.utc)
    audit(db, 'PUBLICAR', actor, {'cut_id': str(cut_id), 'previous_cut': cut.context.get('previous_cut'), 'counts': counts})
    db.commit()


def status(db) -> dict:
    publication = db.get(RiskPublication, 1)
    snapshot = db.info.get('public_snapshot')
    selected = snapshot['risk_cut_id'] if snapshot else (publication.cut_id if publication else None)
    cut = db.get(RiskCut,selected) if selected else None
    latest = db.query(RiskCut).order_by(RiskCut.created_at.desc()).first()
    return {'available': cut is not None, 'cut_id': str(cut.id) if cut else None,
            'data_cut_at': cut.context.get('data_cut_at') if cut else None,
            'public_cut_id': snapshot['id'] if snapshot else None,
            'public_data_cut_at': snapshot['data_cut_at'] if snapshot else None,
            'daily_enabled': publication.daily_enabled if publication else False,
            'last_attempt_day': publication.last_attempt_day if publication else None,
            'last_success_day': publication.last_success_day if publication else None,
            'update_status': latest.status if latest else 'PENDIENTE_MODELOS',
            'message': 'Índice pendiente de modelos validados y un corte completo.' if not cut else 'Índice de prioridad de revisión; no acredita corrupción.'}
