"""Synthetic proof fixtures check integrity, never establish real labels."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import pytest
from analytics_ml.evidence import validate_record, verified_observations
from modules.motor_riesgo.domain import digest
from test_risk_engine import observation


def reviewed_record(root: Path, item=None):
    root.mkdir(parents=True, exist_ok=True)
    body=b'SYNTHETIC ENGINEERING FIXTURE: not a procurement document or judicial label.'
    (root/'original.txt').write_bytes(body)
    checksum=hashlib.sha256(body).hexdigest()
    item=deepcopy(item or observation())
    item.update(stage_event_at=item['prediction_at'],temporal_scope='historical_stage_snapshot')
    for field in item['fields'].values():
        field['sha256']=digest({'SRC':checksum})
    # Explicitly synthetic nominal COP inputs, never inferred from a real PDF.
    from analytics_ml.evidence import MONETARY_MEASURES
    for name, measure in MONETARY_MEASURES.items():
        field=item['fields'].get(name)
        if field and field.get('value') is not None:
            field['monetary']={'raw_amount':str(math.expm1(field['value'])), 'currency':'COP',
                'unit':'PESOS','price_basis':'NOMINAL','measure':measure,'transform':'LOG1P'}
    return {'evidence_id':'fixture-review', 'observation':item,
            'review':{key:True for key in ('dates_verified','values_verified','identity_verified','stage_verified','monetary_basis_verified')},
            'documents':[{'document_id':'SRC','file':'original.txt','sha256':checksum,
                          'url':'https://www.datos.gov.co/resource/p6dx-8zbt.json',
                          'available_at':item['prediction_at'],'temporal_basis':'ORIGINAL_DATED_DOCUMENT'}],
            'field_evidence':{name:{'document_ids':['SRC'],'locator':'synthetic fixture field '+name,
                                    **({'monetary_sha256':digest(field['monetary']), 'monetary_locator':'synthetic nominal COP amount '+name} if field.get('monetary') else {}),
                                    'value_sha256':digest(field['value'])} for name,field in item['fields'].items()}}


def entry(record):
    return {'record':record,'record_sha256':digest(record),'registered_by':1}


def test_hash_declaration_without_separate_review_never_becomes_training_evidence(tmp_path):
    rows,report=verified_observations([observation()],[],tmp_path)
    assert rows==[] and report['excluded']=={'sin_registro_de_evidencia_revisada':1}


def test_preserved_sources_and_exact_reviewed_snapshot_are_required(tmp_path):
    record=reviewed_record(tmp_path)
    item={**record['observation'],'feature_evidence_id':record['evidence_id']}
    rows,report=verified_observations([item],[entry(record)],tmp_path)
    assert rows==[item] and report['verified_rows']==1
    changed=deepcopy(item);changed['fields']['log_presupuesto']['value']=99
    assert verified_observations([changed],[entry(record)],tmp_path)[1]['excluded']=={'observacion_distinta_de_revision':1}
    (tmp_path/'original.txt').write_bytes(b'altered')
    assert verified_observations([item],[entry(record)],tmp_path)[1]['excluded']=={'evidencia_fisica_no_verificada':1}


@pytest.mark.parametrize('tamper', ['review','date','capture','path','hash','locator','value','field_hash','scope','stage_time'])
def test_invalid_source_dates_paths_or_unreviewed_extractions_fail(tmp_path,tamper):
    record=reviewed_record(tmp_path)
    doc=record['documents'][0]
    if tamper=='review': record['review']['dates_verified']=False
    elif tamper=='date': doc['available_at']='2021-01-01T00:00:00Z'
    elif tamper=='capture': doc.update(temporal_basis='CAPTURE_LOG',captured_at='2026-10-16T00:00:00Z')
    elif tamper=='path': doc['file']='../outside.txt'
    elif tamper=='hash': doc['sha256']='f'*64
    elif tamper=='locator': record['field_evidence']['categoria']['locator']=' '
    elif tamper=='value': record['field_evidence']['categoria']['value_sha256']='f'*64
    elif tamper=='field_hash': record['observation']['fields']['categoria']['sha256']='f'*64
    elif tamper=='scope': record['observation']['temporal_scope']='observed_at_capture_not_backdated'
    elif tamper=='stage_time': record['observation']['stage_event_at']='2019-01-01T00:00:00Z'
    with pytest.raises(ValueError): validate_record(record,tmp_path)


def test_cli_training_blocks_unreviewed_observations_before_fitting(tmp_path):
    for name,content in [('cases.json','[]'),('registry.json','[]'),('data.jsonl',json.dumps(observation())+'\n')]:
        (tmp_path/name).write_text(content,encoding='utf-8')
    output=tmp_path/'training.json'
    script=Path(__file__).resolve().parents[1]/'scripts/risk_process.py'
    result=subprocess.run([sys.executable,'-I',str(script),'train','--cases',str(tmp_path/'cases.json'),
        '--feature-evidence',str(tmp_path/'registry.json'),'--evidence',str(tmp_path),
        '--observations',str(tmp_path/'data.jsonl'),'--output',str(output)],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    report=json.loads(output.read_text(encoding='utf-8'))
    assert report['feature_evidence']['verified_rows']==0
    assert all(item['blocked'] and 'artifact' not in item for item in report['stages'].values())
    assert report['inputs']['feature_evidence_sha256']==digest([])


def test_authenticated_review_persists_and_matches_only_exact_secop_identity(postgres_test_session,tmp_path,monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from main import app
    from core.database import get_db
    from gateway.middlewares.auth_middleware import get_current_admin
    from modules.motor_riesgo import service
    from modules.motor_riesgo.models import RiskFeatureEvidence
    from modules.auth.model.Admin import Admin
    from test_risk_engine_postgres import source,row
    from datetime import date
    from uuid import uuid4
    db=postgres_test_session;src=source(db);raw,_=row(db,src,1,date(2020,1,1))
    admin=Admin(username='evidence-'+uuid4().hex,email=uuid4().hex+'@example.test',hashed_password='synthetic-unused')
    db.add(admin);db.flush()
    item=observation(raw_secop_id=raw.id,source_id=src.id,source_row_id=raw.socrata_row_id,process_id=raw.id_del_proceso)
    record=reviewed_record(tmp_path/'evidence',item)
    monkeypatch.setattr(service,'work_root',lambda:tmp_path)
    app.dependency_overrides[get_db]=lambda:db
    try:
        with TestClient(app) as client:
            assert client.post('/api/riesgo/admin/evidencias-variables',json={'record':record}).status_code in (401,403)
            app.dependency_overrides[get_current_admin]=lambda:SimpleNamespace(id=admin.id)
            response=client.post('/api/riesgo/admin/evidencias-variables',json={'record':record})
            assert response.status_code==200,response.text
            persisted=db.get(RiskFeatureEvidence,record['evidence_id'])
            assert persisted.registered_by==admin.id and persisted.record_sha256==digest(record)
            assert persisted.raw_secop_id==raw.id and persisted.stage=='CONVOCATORIA'
            assert client.get('/api/riesgo/admin/evidencias-variables').json()['total']==1
            assert client.post('/api/riesgo/admin/evidencias-variables',json={'record':record}).status_code==422
            changed=deepcopy(record);changed['evidence_id']='unmatched';changed['observation']['process_id']='NOT-IN-SOURCE'
            assert client.post('/api/riesgo/admin/evidencias-variables',json={'record':changed}).status_code==422
            changed=deepcopy(record);changed['evidence_id']='wrong-raw';changed['observation']['raw_secop_id']=raw.id+1
            assert client.post('/api/riesgo/admin/evidencias-variables',json={'record':changed}).status_code==422
    finally:
        app.dependency_overrides.pop(get_db,None);app.dependency_overrides.pop(get_current_admin,None)


@pytest.mark.parametrize('tamper',[None,'conflict','physical','record_hash','raw_identity','event_date','registered_later'])
def test_batch_inference_uses_only_exact_reviewed_stage_values(postgres_test_session,tmp_path,monkeypatch,tamper):
    from datetime import date,datetime,timezone
    from uuid import uuid4
    from modules.motor_riesgo import service
    from modules.motor_riesgo.models import RiskFeatureEvidence
    from modules.motor_riesgo.feature_store import export_observations
    from modules.auth.model.Admin import Admin
    from analytics_ml.inference import predict
    from test_risk_engine import artifact
    from test_risk_engine_postgres import source,row
    db=postgres_test_session;src=source(db);raw,cp=row(db,src,1,date(2020,1,1),amount=900)
    admin=Admin(username='batch-'+uuid4().hex,email=uuid4().hex+'@example.test',hashed_password='synthetic-unused')
    db.add(admin);db.flush();monkeypatch.setattr(service,'work_root',lambda:tmp_path)
    item=observation(raw_secop_id=raw.id,source_id=src.id,source_row_id=raw.socrata_row_id,process_id=raw.id_del_proceso)
    record=reviewed_record(tmp_path/'evidence',item);service.register_feature_evidence(db,record,admin.id)
    saved=db.get(RiskFeatureEvidence,record['evidence_id'])
    duplicate=deepcopy(record);duplicate['evidence_id']='second-review'
    if tamper=='conflict':
        duplicate['observation']['fields']['log_presupuesto']['value']=2
        duplicate['field_evidence']['log_presupuesto']['value_sha256']=digest(2)
        money=duplicate['observation']['fields']['log_presupuesto']['monetary']
        money['raw_amount']=str(math.expm1(2))
        duplicate['field_evidence']['log_presupuesto']['monetary_sha256']=digest(money)
    service.register_feature_evidence(db,duplicate,admin.id)
    if tamper=='physical':(tmp_path/'evidence/original.txt').write_bytes(b'tampered fixture')
    elif tamper=='record_hash':saved.record_sha256='f'*64
    elif tamper=='raw_identity':
        changed=deepcopy(saved.record);changed['observation']['raw_secop_id']=raw.id+1
        saved.record=changed;saved.record_sha256=digest(changed)
    elif tamper=='event_date':raw.fecha_de_publicacion_del=datetime(2020,1,2,tzinfo=timezone.utc)
    elif tamper=='registered_later':
        for entry in db.query(RiskFeatureEvidence):entry.created_at=datetime(2031,1,1,tzinfo=timezone.utc)
    db.flush();path=tmp_path/'batch.jsonl'
    export_observations(db,path,[src.id],'2030-01-01T12:00:00+00:00')
    output=json.loads(path.read_text());result=predict(artifact(),output)
    if tamper:
        assert result['index'] is None
        assert output['temporal_scope']=='observed_at_capture_not_backdated'
    else:
        assert result['index']==50 and result['values']['log_presupuesto']==1
        assert output['prediction_at']==item['prediction_at']
        assert output['feature_evidence_id']=='fixture-review'
        assert output['temporal_scope']=='historical_stage_snapshot'
    assert db.get(type(raw),raw.id).precio_base==900


@pytest.mark.parametrize('extra_award',[False,True,'unnormalized'])
def test_both_stages_reuse_exact_training_features_without_current_award_leakage(postgres_test_session,tmp_path,monkeypatch,extra_award):
    from datetime import date,datetime,timezone
    from uuid import uuid4
    from modules.motor_riesgo import service
    from modules.motor_riesgo.feature_store import export_observations
    from modules.auth.model.Admin import Admin
    from analytics_ml.corpus import prepare_rows
    from analytics_ml.inference import predict
    from test_risk_engine import artifact
    from test_risk_engine_postgres import source,row
    db=postgres_test_session;src=source(db);raw,cp=row(db,src,1,date(2020,1,1),amount=900)
    raw.adjudicado='SI';raw.estado_del_procedimiento='Seleccionado'
    raw.fecha_adjudicacion=datetime(2020,2,1,tzinfo=timezone.utc)
    admin=Admin(username='both-'+uuid4().hex,email=uuid4().hex+'@example.test',hashed_password='synthetic-unused')
    db.add(admin);db.flush();monkeypatch.setattr(service,'work_root',lambda:tmp_path)
    registry=[]
    for stage in ('CONVOCATORIA','ADJUDICACION'):
        at=raw.fecha_adjudicacion if stage=='ADJUDICACION' else raw.fecha_de_publicacion_del
        item=observation(stage,raw_secop_id=raw.id,source_id=src.id,source_row_id=raw.socrata_row_id,
            process_id=raw.id_del_proceso,award_id=raw.id_adjudicacion if stage=='ADJUDICACION' else None,prediction_at=at.isoformat())
        for field in item['fields'].values():field['available_at']=item['prediction_at']
        record=reviewed_record(tmp_path/'evidence',item);record['evidence_id']='review-'+stage
        service.register_feature_evidence(db,record,admin.id)
        registry.append({**entry(record),'registered_by':admin.id})
    if extra_award:
        other,other_cp=row(db,src,2,date(2020,1,1),process=raw.id_del_proceso,amount=999)
        other.adjudicado='SI';other.estado_del_procedimiento='Seleccionado';other.fecha_adjudicacion=raw.fecha_adjudicacion
        if extra_award=='unnormalized':db.delete(other_cp)
        db.flush()
    path=tmp_path/'both.jsonl';counts=export_observations(db,path,[src.id],'2030-01-01T12:00:00+00:00')
    captured=list(map(json.loads,path.read_text().splitlines()))
    if extra_award:
        assert counts=={'CONVOCATORIA':0,'ADJUDICACION':1 if extra_award=='unnormalized' else 2}
        first=next(item for item in captured if item['raw_secop_id']==raw.id)
        assert first['stage']=='ADJUDICACION' and predict(artifact('ADJUDICACION'),first)['index']==50
        assert json.loads(path.with_suffix('.coverage.json').read_text())['exclusions']['identidad_operacion_ambigua']==1
        return
    assert counts=={'CONVOCATORIA':1,'ADJUDICACION':1}
    accepted,summary=verified_observations(captured,registry,tmp_path/'evidence')
    assert summary['verified_rows']==2
    for stage in counts:
        training,coverage=prepare_rows(accepted,{},stage)
        result=predict(artifact(stage),next(item for item in captured if item['stage']==stage))
        assert len(training)==1 and training[0]['values']==result['values']
        assert result['index']==50 and result['values']['log_presupuesto']==1
        assert ('log_adjudicado' in result['values'])==(stage=='ADJUDICACION')
    assert raw.precio_base==raw.valor_total_adjudicacion==900


def test_daily_capture_does_not_compute_unusable_current_history_contexts(postgres_test_session,tmp_path,monkeypatch):
    from datetime import date
    from modules.motor_riesgo.feature_store import export_observations
    from test_risk_engine_postgres import source,row
    from test_risk_engine import artifact
    from analytics_ml.inference import predict
    db=postgres_test_session;src=source(db);raw,_=row(db,src,1,date(2020,1,1))
    def forbidden(*args,**kwargs):raise AssertionError('Current rolling contexts do not reconstruct stage history')
    monkeypatch.setattr('modules.motor_riesgo.feature_store.prepare_context',forbidden)
    path=tmp_path/'lean.jsonl'
    assert export_observations(db,path,[src.id],'2030-01-01T00:00:00Z')=={'CONVOCATORIA':1,'ADJUDICACION':0}
    record=json.loads(path.read_text());result=predict(artifact(),record)
    assert record['raw_secop_id']==raw.id and record['observed']['budget']=='100.00'
    assert 'procesos_previos' not in record['fields'] and result['index'] is None
    assert 'sin_reconstruccion_temporal_de_etapa' in result['reasons']
    coverage=json.loads(path.with_suffix('.coverage.json').read_text())
    assert coverage['raw_rows_read']==coverage['normalized_rows_read']==1 and coverage['capture_mode']=='reviewed_stage_evidence'


def test_admin_training_freezes_the_registry_and_reports_unreviewed_rows(postgres_test_session,tmp_path,monkeypatch):
    import os
    from uuid import uuid4
    from modules.motor_riesgo import service
    interpreter=os.environ.get('TEST_ML_PYTHON')
    if not interpreter: pytest.skip('TEST_ML_PYTHON explícito requerido')
    monkeypatch.setattr(service,'work_root',lambda:tmp_path)
    monkeypatch.setattr(service.settings,'RISK_TRAINING_PYTHON',interpreter)
    dataset=tmp_path/'manual.jsonl'
    dataset.write_text(json.dumps(observation())+'\n',encoding='utf-8')
    identifier=uuid4()
    output=service.train_job(postgres_test_session,dataset.name,identifier)
    assert not output['models'] and len(output['blocked'])==2
    assert output['feature_evidence']['verified_rows']==0
    assert output['feature_evidence']['excluded']=={'sin_registro_de_evidencia_revisada':1}
    manifest=json.loads((tmp_path/'runs'/str(identifier)/'inputs.json').read_text())
    assert manifest['feature_evidence_sha256']==digest([])
    assert service.train_job(postgres_test_session,dataset.name,identifier)['models']=={}
