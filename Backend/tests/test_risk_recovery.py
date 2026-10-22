"""Recovery preserves a verified file and committed batches, without re-fitting."""
from copy import deepcopy
from datetime import date
import json
import os
from pathlib import Path
from uuid import uuid4
import pytest
from analytics_ml.streams import binary_stream,logical_sha256
from modules.motor_riesgo.domain import STAGES
from modules.motor_riesgo.inference_artifact import completed_inference
from modules.motor_riesgo.models import RiskCut,RiskResult
from modules.motor_riesgo.result_store import persist_results
from test_risk_engine import artifact,observation


def inputs(tmp_path,monkeypatch,raw_ids=(1,)):
    from modules.motor_riesgo import service
    interpreter=os.environ.get('TEST_ML_INFERENCE_PYTHON')
    if not interpreter:pytest.skip('TEST_ML_INFERENCE_PYTHON explícito requerido')
    monkeypatch.setattr(service,'work_root',lambda:tmp_path)
    models={stage:artifact(stage) for stage in STAGES}
    path=tmp_path/'observations.jsonl.gz'
    with binary_stream(path,'xb') as stream:
        for key in raw_ids:
            stream.write((json.dumps(observation(raw_secop_id=key))+'\n').encode())
    context={'observations_sha256':logical_sha256(path),'counts':{'CONVOCATORIA':len(raw_ids),'ADJUDICACION':0}}
    return path,context,models,interpreter


@pytest.mark.parametrize('tamper',[None,'file','input','model','code','counts'])
def test_only_complete_matching_immutable_output_can_be_reused(tmp_path,monkeypatch,tamper):
    path,context,models,interpreter=inputs(tmp_path,monkeypatch)
    output,manifest=completed_inference(tmp_path,path,context,models,interpreter)
    assert output.parent.name=='inference-complete'
    if tamper=='file':output.write_bytes(b'changed')
    elif tamper=='input':context['observations_sha256']='f'*64
    elif tamper=='model':models['CONVOCATORIA']['sha256']='f'*64
    elif tamper in ('code','counts'):
        value=deepcopy(manifest)
        if tamper=='code':value['prediction_code_sha256']={}
        else:value['evaluated_counts']['CONVOCATORIA']=2
        Path(str(output)+'.manifest.json').write_text(json.dumps(value),encoding='utf-8')
    if tamper:
        with pytest.raises(ValueError):completed_inference(tmp_path,path,context,models,'must-not-run.exe')
    else:
        assert completed_inference(tmp_path,path,context,models,'must-not-run.exe')==(output,manifest)
    assert len(list(tmp_path.glob('inference-attempt-*')))==0


def test_interrupted_attempt_never_becomes_a_complete_artifact(tmp_path,monkeypatch):
    from modules.motor_riesgo import service
    path,context,models,interpreter=inputs(tmp_path,monkeypatch)
    actual=service.run_process
    def interrupted(_interpreter,args):
        Path(args[args.index('--output')+1]).write_bytes(b'incomplete engineering fixture')
        raise RuntimeError('synthetic process crash')
    monkeypatch.setattr(service,'run_process',interrupted)
    with pytest.raises(RuntimeError):completed_inference(tmp_path,path,context,models,interpreter)
    assert not (tmp_path/'inference-complete').exists()
    monkeypatch.setattr(service,'run_process',actual)
    output,manifest=completed_inference(tmp_path,path,context,models,interpreter)
    assert manifest['input_rows']==1 and output.is_file()
    assert len(list(tmp_path.glob('inference-attempt-*')))==1


def test_result_cursor_and_rows_commit_together_and_resume_without_reinserting(postgres_test_session,tmp_path,monkeypatch):
    from test_risk_engine_postgres import source,row
    from sqlalchemy import event
    db=postgres_test_session;src=source(db)
    ids=[row(db,src,i,date(2020,1,1))[0].id for i in range(5)]
    path,context,models,interpreter=inputs(tmp_path,monkeypatch,ids)
    output,manifest=completed_inference(tmp_path,path,context,models,interpreter)
    cut=RiskCut(id=uuid4(),status='PREPARANDO',context=context)
    db.add(cut);db.commit();identifier=cut.id
    actual=db.commit;confirmed=[]
    def interrupted():
        actual();confirmed.append(True)
        raise RuntimeError('synthetic loss after commit')
    monkeypatch.setattr(db,'commit',interrupted)
    with pytest.raises(RuntimeError):persist_results(db,identifier,output,manifest,batch_size=2)
    monkeypatch.setattr(db,'commit',actual)
    db.rollback()
    assert confirmed==[True] and db.query(RiskResult).count()==2
    assert db.get(RiskCut,identifier).context['persistence_checkpoint']['lines']==2
    assert persist_results(db,identifier,output,manifest,batch_size=2)==context['counts']
    assert db.query(RiskResult).count()==5
    assert db.get(RiskCut,identifier).context['persistence_checkpoint']['lines']==5
    statements=[];bind=db.get_bind()
    def record(connection,cursor,statement,parameters,execution,many):statements.append(statement)
    event.listen(bind,'before_cursor_execute',record)
    try:assert persist_results(db,identifier,output,manifest)==context['counts']
    finally:event.remove(bind,'before_cursor_execute',record)
    assert not any(statement.upper().startswith('INSERT') for statement in statements)


@pytest.mark.parametrize('tamper',['lines','counts','hash','rows'])
def test_inconsistent_result_cursor_cannot_silently_skip_data(postgres_test_session,tmp_path,monkeypatch,tamper):
    from test_risk_engine_postgres import source,row
    db=postgres_test_session;src=source(db);raw,_=row(db,src,1,date(2020,1,1))
    path,context,models,interpreter=inputs(tmp_path,monkeypatch,[raw.id])
    output,manifest=completed_inference(tmp_path,path,context,models,interpreter)
    cut=RiskCut(id=uuid4(),status='PREPARANDO',context=context);db.add(cut);db.commit()
    persist_results(db,cut.id,output,manifest)
    if tamper=='rows':db.query(RiskResult).filter_by(cut_id=cut.id).delete();db.flush()
    else:
        value=deepcopy(cut.context)
        if tamper=='lines':value['persistence_checkpoint']['lines']=2
        elif tamper=='counts':value['persistence_checkpoint']['counts']['CONVOCATORIA']=0
        else:value['persistence_checkpoint']['output_sha256']='f'*64
        cut.context=value;db.flush()
    with pytest.raises(ValueError):persist_results(db,cut.id,output,manifest)
