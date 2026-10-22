from datetime import date,datetime,timezone,timedelta
from decimal import Decimal
from sqlalchemy import text
from types import SimpleNamespace
from uuid import uuid4
import hashlib
import pytest
from fastapi.testclient import TestClient
from main import app
from core.database import get_db
from gateway.middlewares.auth_middleware import get_current_admin
from modules.analitica.repository.repository import AnaliticaRepository
from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.ingesta.model.RawSecop import RawSecop
from modules.transformacion.model.ContratoProcesado import ContratoProcesado
from modules.motor_riesgo.models import RiskCut,RiskResult,RiskPublication,RiskModel
from modules.motor_riesgo.service import publish,activate
from modules.motor_riesgo.pipeline import export_observations,enqueue_daily
from shared.enums import TipoFormato


def source(db):
    item=FuenteDatos(nombre='risk-'+uuid4().hex,tipo='SECOP',formato=TipoFormato.JSON,
                     endpoint='https://www.datos.gov.co/resource/p6dx-8zbt.json',activo=False)
    db.add(item); db.flush()
    return item


def row(db,src,index,day,*,provider='900000001',process=None,category='80160000',amount=100,incomplete=False):
    process=process or f'P-{src.id}-{index}'
    raw=RawSecop(fuente_id=src.id,socrata_row_id=uuid4().hex,id_del_proceso=process,
                 id_adjudicacion=f'AWARD-{index}',codigo_principal_de_categoria=category,precio_base=amount,valor_total_adjudicacion=amount,
                 modalidad_de_contratacion='CONTRATACION DIRECTA',fecha_de_publicacion_del=datetime.combine(day,datetime.min.time(),tzinfo=timezone.utc),
                 adjudicado='NO',estado_del_procedimiento='Publicado')
    db.add(raw);db.flush()
    cp=ContratoProcesado(raw_secop_id=raw.id,id_del_proceso=process,nit_entidad=str(src.id),entidad_normalizada=f'ENTIDAD {src.id}',
                          nit_proveedor=provider,nit_proveedor_clave=provider,proveedor_normalizado='HOMONIMO',
                          fecha_publicacion_normalizada=day,valor_total_normalizado=amount,precio_base_normalizado=amount,
                          modalidad_contratacion='CONTRATACION DIRECTA',tipo_contrato_normalizado='SERVICIOS',
                          normalized_hash=hashlib.sha256(uuid4().bytes).hexdigest(),es_incompleto=incomplete)
    db.add(cp);db.flush()
    return raw,cp


def test_iqr_cohorts_minimum_and_independent_missing_field(postgres_test_session):
    db=postgres_test_session;src=source(db)
    for i in range(31):
        row(db,src,i,date(2012,1,1),amount=i+1,incomplete=True)
    for i in range(29):
        row(db,src,100+i,date(2012,1,1),category='SMALL',amount=i+1)
    repo=AnaliticaRepository(db)
    stats=repo.obtener_estadisticas_por_grupo('valor_total_normalizado',fecha_desde=date(2012,1,1),fecha_hasta=date(2012,1,1))
    assert len(stats)==1 and stats[0]['total_contratos']==31
    assert '80160000|' in stats[0]['grupo']
    analyzed,outliers=repo.guardar_resultados_outliers_sql(run_id=uuid4(),campo='valor_total_normalizado',
        estadisticas_por_grupo={r['grupo']:r for r in stats},fecha_calculo=datetime.now(timezone.utc),
        fecha_desde=date(2012,1,1),fecha_hasta=date(2012,1,1))
    assert analyzed==31


def test_reiteration_separates_homonyms_and_deduplicates_processes(postgres_test_session):
    db=postgres_test_session;src=source(db)
    first,_=row(db,src,1,date(2013,1,1),process='ONE-'+str(src.id))
    row(db,src,2,date(2013,1,2),process=first.id_del_proceso)
    row(db,src,3,date(2013,1,3),provider='900000002')
    row(db,src,4,date(2013,1,4))
    repo=AnaliticaRepository(db)
    pairs=repo.obtener_pares_duplicados(fecha_desde=date(2013,1,1),fecha_hasta=date(2013,1,4))
    assert len(pairs)==1 and pairs[0]['diferencia_dias']==3
    assert repo.guardar_duplicados_sql(run_id=uuid4(),fecha_calculo=datetime.now(timezone.utc),fecha_desde=date(2013,1,1),fecha_hasta=date(2013,1,4))==1


def test_iqr_aliases_cannot_manufacture_a_thirty_operation_cohort(postgres_test_session):
    db=postgres_test_session;src=source(db)
    for i in range(29):
        row(db,src,i,date(2011,1,1),amount=i+1)
    original,cp=row(db,src,100,date(2011,1,1),amount=1000)
    alias,_=row(db,src,101,date(2011,1,1),amount=1000,process=original.id_del_proceso)
    alias.id_adjudicacion=original.id_adjudicacion;db.flush()
    repo=AnaliticaRepository(db)
    scope={'fecha_desde':date(2011,1,1),'fecha_hasta':date(2011,1,1)}
    assert repo.obtener_estadisticas_por_grupo('valor_total_normalizado',**scope)==[]
    assert len(repo.obtener_contratos_validos('valor_total_normalizado',**scope))==29
    # The same process identifier in a different source is a distinct unit.
    second=source(db)
    other,_=row(db,second,100,date(2011,1,1),amount=100,process=original.id_del_proceso)
    other.id_adjudicacion=original.id_adjudicacion;db.flush()
    stats=repo.obtener_estadisticas_por_grupo('valor_total_normalizado',**scope)
    assert stats[0]['total_contratos']==30
    run_id=uuid4()
    analyzed,_=repo.guardar_resultados_outliers_sql(run_id=run_id,campo='valor_total_normalizado',
        estadisticas_por_grupo={s['grupo']:s for s in stats},fecha_calculo=datetime.now(timezone.utc),**scope)
    assert analyzed==30
    from modules.analitica.model.contrato_outlier import ContratoOutlier
    assert db.query(ContratoOutlier).filter_by(run_id=run_id,contrato_id=cp.id).count()==0


def test_iqr_awards_are_distinct_but_repeated_process_budgets_are_ambiguous(postgres_test_session):
    db=postgres_test_session;src=source(db)
    for i in range(31):
        row(db,src,i,date(2010,1,1),process='MULTI-AWARD',amount=i+1)
    repo=AnaliticaRepository(db)
    scope={'fecha_desde':date(2010,1,1),'fecha_hasta':date(2010,1,1)}
    assert repo.obtener_estadisticas_por_grupo('valor_total_normalizado',**scope)[0]['total_contratos']==31
    assert repo.obtener_estadisticas_por_grupo('precio_base_normalizado',**scope)==[]
    assert repo.obtener_contratos_validos('precio_base_normalizado',**scope)==[]


def test_direct_concentration_finds_intermediate_window_despite_old_history(postgres_test_session):
    db=postgres_test_session;src=source(db)
    for i,day in enumerate((date(2014,1,1),date(2014,7,1),date(2014,7,3),date(2014,7,5),date(2014,12,1))):
        row(db,src,i,day)
    result=AnaliticaRepository(db).calcular_adjudicaciones_directas(fecha_desde=date(2014,1,1),fecha_hasta=date(2014,12,1),minimo_directas=3,dias_ventana=10)
    assert len(result)==1 and result[0]['contratos_directos']==3
    assert result[0]['fecha_contrato']==date(2014,7,5)


def test_public_empty_state_admin_protection_and_activation_gate(postgres_test_session):
    db=postgres_test_session
    app.dependency_overrides[get_db]=lambda:db
    try:
        with TestClient(app) as client:
            result=client.get('/api/riesgo/estado')
            assert result.status_code==200 and result.json()['available'] is False
            assert client.get('/api/riesgo/resultados').json()['items']==[]
            assert client.post('/api/riesgo/admin/activar',json={'convocatoria':str(uuid4()),'adjudicacion':str(uuid4())}).status_code in (401,403)
            app.dependency_overrides[get_current_admin]=lambda:SimpleNamespace(id=1)
            assert client.post('/api/riesgo/admin/activar',json={'convocatoria':str(uuid4()),'adjudicacion':str(uuid4())}).status_code==409
            assert client.post('/api/riesgo/admin/entrenar',json={'dataset':'../../outside.jsonl'}).status_code==422
    finally:
        app.dependency_overrides.pop(get_db,None);app.dependency_overrides.pop(get_current_admin,None)


def test_no_daily_job_or_publication_without_both_validated_models(postgres_test_session):
    db=postgres_test_session
    with pytest.raises(ValueError,match='dos modelos'):
        enqueue_daily(db,manual=True)
    with pytest.raises(ValueError):
        publish(db,uuid4())


def test_daily_catchup_is_not_lost_when_an_older_job_was_still_queued(postgres_test_session):
    from modules.motor_riesgo.pipeline import due_day
    db=postgres_test_session;src=source(db);src.activo=True
    pointer=db.get(RiskPublication,1);pointer.model_ids=synthetic_models(db);pointer.daily_enabled=True
    pointer.last_attempt_day=due_day();pointer.last_success_day='2000-01-01';db.flush()
    job=enqueue_daily(db)
    assert job is not None
    assert enqueue_daily(db).id==job.id
    pointer=db.get(RiskPublication,1);pointer.last_success_day=due_day();db.flush()
    assert enqueue_daily(db) is None


def test_snapshot_export_does_not_backdate_and_omits_unverified_metrics(postgres_test_session,tmp_path):
    import json
    db=postgres_test_session;src=source(db)
    raw,cp=row(db,src,1,date(2015,1,1),incomplete=True)
    at='2026-10-16T12:00:00+00:00'
    path=tmp_path/'observations.jsonl'
    counts=export_observations(db,path,[src.id],at)
    data=json.loads(path.read_text().splitlines()[0])
    assert counts=={'CONVOCATORIA':1,'ADJUDICACION':0}
    assert data['prediction_at']==at
    assert 'oferentes' not in data['fields'] and 'plazo_dias' not in data['fields']
    assert data['source_row_id']==raw.socrata_row_id


def test_history_uses_known_awards_exact_time_and_excludes_current_process(postgres_test_session,tmp_path):
    import json
    db=postgres_test_session;src=source(db)
    current,_=row(db,src,1,date(2026,10,1),process='CURRENT',amount=100)
    old,_=row(db,src,2,date(2024,1,1),amount=200)
    future,_=row(db,src,3,date(2026,10,1),amount=900)
    future_publication,_=row(db,src,4,date(2026,10,16),amount=800)
    row(db,src,5,date(2026,10,15),amount=700)  # supplier not yet awarded: no relationship
    second,_=row(db,src,6,date(2026,10,1),process='CURRENT',amount=50)
    for raw,award_time in ((current,datetime(2026,10,16,10,tzinfo=timezone.utc)),
            (old,datetime(2026,10,15,10,tzinfo=timezone.utc)),(future,datetime(2026,10,16,13,tzinfo=timezone.utc)),
            (future_publication,datetime(2026,10,16,11,tzinfo=timezone.utc)),(second,datetime(2026,10,16,11,tzinfo=timezone.utc))):
        raw.adjudicado='SI';raw.id_adjudicacion='A-'+str(raw.id);raw.fecha_adjudicacion=award_time
        raw.estado_del_procedimiento='Seleccionado'
    future_publication.fecha_de_publicacion_del=datetime(2026,10,16,13,tzinfo=timezone.utc)
    db.flush();path=tmp_path/'history.jsonl'
    export_observations(db,path,[src.id],'2026-10-16T12:00:00+00:00',include_current_context=True)
    data={r['raw_secop_id']:r for r in map(json.loads,path.read_text().splitlines())}
    result=data[current.id];values={k:v['value'] for k,v in result['fields'].items()}
    assert future.id not in data and future_publication.id not in data
    assert values['reiteraciones_30d']==values['directas_90d']==1
    assert values['procesos_previos']==2
    assert values['concentracion_previa']==1
    assert result['context']['directas_90d']['amount'] is None
    assert result['context']['directas_90d']['amount_reason']=='moneda_no_documentada_en_fuente_local'
    assert result['context']['concentracion_previa']['processes']==1


def test_duplicate_operation_rows_abstain_and_missing_date_keeps_other_features(postgres_test_session,tmp_path):
    import json
    from test_risk_engine import artifact
    from analytics_ml.inference import predict
    db=postgres_test_session;src=source(db)
    first,_=row(db,src,1,date(2026,10,1),process='SAME')
    row(db,src,2,date(2026,10,1),process='SAME')
    missing,_=row(db,src,3,date(2026,10,1));missing.fecha_de_publicacion_del=None
    db.flush();path=tmp_path/'duplicates.jsonl'
    export_observations(db,path,[src.id],'2026-10-16T12:00:00+00:00',include_current_context=True)
    data={r['raw_secop_id']:r for r in map(json.loads,path.read_text().splitlines())}
    result=predict(artifact(),data[first.id])
    assert result['index'] is None and 'identidad_operacion_ambigua' in result['reasons']
    result=predict(artifact(),data[missing.id])
    assert result['index'] is None and 'fecha_etapa_ausente' in result['reasons']
    assert 'sin_reconstruccion_temporal_de_etapa' in result['reasons']
    assert result['values']['log_presupuesto'] is not None


def test_history_does_not_merge_equal_process_ids_from_distinct_sources(postgres_test_session,tmp_path):
    import json
    db=postgres_test_session;one=source(db);two=source(db)
    current,_=row(db,one,1,date(2026,10,15),process='CURRENT')
    for src in (one,two):
        raw,cp=row(db,src,2,date(2026,10,14),process='REUSED')
        cp.nit_entidad=str(one.id)
        raw.adjudicado='SI';raw.id_adjudicacion='A-'+str(raw.id)
        raw.fecha_adjudicacion=datetime(2026,10,14,10,tzinfo=timezone.utc)
    db.flush();path=tmp_path/'sources.jsonl'
    export_observations(db,path,[one.id,two.id],'2026-10-16T12:00:00+00:00',include_current_context=True)
    result=next(r for r in map(json.loads,path.read_text().splitlines()) if r['raw_secop_id']==current.id)
    assert result['fields']['procesos_previos']['value']==2
    assert result['context']['concentracion_previa']['processes']==2


def test_source_revisions_detect_in_place_updates_and_rollback_transactionally(postgres_test_session):
    from modules.motor_riesgo.pipeline import signature
    db=postgres_test_session;src=source(db)
    before=signature(db)
    raw,cp=row(db,src,1,date(2026,1,1))
    inserted=signature(db)
    assert inserted['rows']==before['rows']+1 and inserted['normalized_rows']==before['normalized_rows']+1
    old_time=raw.sincronizado_en
    raw.entidad='CAMBIO SIN MODIFICAR FECHA';db.flush()
    updated=signature(db)
    assert updated!=inserted and updated['rows']==inserted['rows'] and raw.sincronizado_en==old_time
    # Empty statements must not manufacture a new data generation.
    db.execute(text('UPDATE raw_secop SET entidad=entidad WHERE id=-1'))
    assert signature(db)==updated
    savepoint=db.begin_nested()
    row(db,src,2,date(2026,1,2))
    assert signature(db)['rows']==updated['rows']+1
    savepoint.rollback()
    assert signature(db)==updated
    db.delete(cp);db.flush();db.delete(raw);db.flush()
    deleted=signature(db)
    assert deleted['rows']==before['rows'] and deleted['normalized_rows']==before['normalized_rows']


def test_source_revisions_count_upserts_once_and_handle_empty_writes(postgres_test_session):
    from sqlalchemy.dialects.postgresql import insert
    from modules.motor_riesgo.pipeline import signature
    db=postgres_test_session;src=source(db)
    raw,_=row(db,src,1,date(2026,1,1));before=signature(db)
    statement=insert(RawSecop).values(fuente_id=src.id,socrata_row_id=raw.socrata_row_id,entidad='UPDATING EXISTING')
    db.execute(statement.on_conflict_do_update(index_elements=['fuente_id','socrata_row_id'],set_={'entidad':'UPDATING EXISTING'}))
    after=signature(db)
    assert after['rows']==before['rows'] and after['revisions']['raw_secop'][1]>before['revisions']['raw_secop'][1]
    db.execute(statement.on_conflict_do_nothing(index_elements=['fuente_id','socrata_row_id']))
    assert signature(db)==after


def test_source_signature_reads_only_the_two_control_rows(postgres_test_session):
    from sqlalchemy import event
    from modules.motor_riesgo.pipeline import signature
    db=postgres_test_session;statements=[];connection=db.connection()
    def record(_conn,_cursor,statement,_params,_context,_many):
        statements.append(statement)
    event.listen(connection,'before_cursor_execute',record)
    try:
        for _ in range(20):
            assert signature(db)['rows']>=0
    finally:
        event.remove(connection,'before_cursor_execute',record)
    assert len(statements)==20 and all('FROM riesgo_versiones_datos' in s for s in statements)


def test_raw_batch_advances_past_missing_normalization_and_reports_the_gap(postgres_test_session,tmp_path):
    import json
    db=postgres_test_session;src=source(db)
    missing=RawSecop(fuente_id=src.id,socrata_row_id=uuid4().hex,id_del_proceso='NOT-NORMALIZED')
    db.add(missing);db.flush()
    valid,_=row(db,src,2,date(2026,1,1))
    path=tmp_path/'gaps.jsonl'
    counts=export_observations(db,path,[src.id],'2026-10-16T12:00:00+00:00')
    coverage=json.loads(path.with_suffix('.coverage.json').read_text(encoding='utf-8'))
    assert coverage['raw_rows_read']==coverage['source_rows']==2
    assert coverage['normalized_rows_read']==coverage['observed_rows']==1
    assert coverage['not_normalized_rows']==1 and counts['CONVOCATORIA']==1
    assert json.loads(path.read_text())['raw_secop_id']==valid.id


def synthetic_models(db):
    # Only this rollback-isolated engineering fixture creates approved records.
    # It does not establish judicial evidence or exercise statistical approval.
    from test_risk_engine import artifact
    from modules.motor_riesgo.domain import digest
    ids={}
    for stage in ('CONVOCATORIA','ADJUDICACION'):
        model=artifact(stage);model['version']=str(uuid4())
        manifest={'synthetic_engineering_fixture':True}
        model['dataset_sha256']=digest({'synthetic_engineering_fixture':True})
        from analytics_ml.evidence import POLICY
        evidence={'policy':POLICY,'registry_sha256':digest({'synthetic_engineering_fixture':True}),
                  'verified_rows':15,'verified_dataset_sha256':model['dataset_sha256']}
        model['feature_evidence_sha256']=digest(evidence)
        model['runtime_manifest_sha256']=digest(manifest)
        from analytics_ml.evaluation import SPLIT_POLICY
        split_audit={'policy':SPLIT_POLICY,'input_rows':15,'split_sizes':[5,5,5],
                     'excluded_rows':0,'exclusions':{'case_group_outside_assigned_chronological_block':0},
                     'demoted_future_labels':[0,0,0],
                     'boundaries':{'validation_from':'2021-01-01T00:00:00Z','test_from':'2022-01-01T00:00:00Z'},
                     'label_cutoffs':['2021-01-01T00:00:00Z','2022-01-01T00:00:00Z',None]}
        model['split_audit_sha256']=digest(split_audit)
        model['sha256']=digest({k:v for k,v in model.items() if k!='sha256'})
        report={'stage':stage,'version':model['version'],'artifact_sha256':model['sha256'],'validated':True,
                'positive_target':'CORRUPCION','dataset_sha256':model['dataset_sha256'],
                'feature_evidence':evidence,'split_sizes':[5,5,5],'split_audit':split_audit,
                'split_case_counts':[5,5,5], 'synthetic_engineering_fixture':True, 'runtime_manifest':manifest,
                'baseline_complete_for_comparison':True,
                'baseline_coverage':{'policy':'binary-family-coverage-v1','complete_rows':5,'total_rows':5,
                                     'operation_coverage_sha256':digest({'synthetic_coverage_fixture':True})},
                'case_interval':{'passed':True,'cases':5,'lower95':.1,'method':'paired_case_bootstrap_fixed_top5_tie_aware','repetitions':2000},
                'unseen_suppliers':{'passed':True,'cases':5,'lower95':.1,'method':'paired_case_bootstrap_fixed_top5_tie_aware','repetitions':2000}}
        report['sha256']=digest(report)
        model_id=uuid4();db.add(RiskModel(id=model_id,stage=stage,version=model['version'],artifact=model,report=report,validated=True))
        ids[stage]=str(model_id)
    db.flush()
    from modules.motor_riesgo.publication import initialize_baseline
    initialize_baseline(db,'2026-10-01')
    return ids


def citizen_context(db):
    from modules.motor_riesgo.publication import checkpoint
    from modules.motor_riesgo.public_aggregates import prepare_aggregates
    revision=checkpoint(db)
    return {'citizen_revision':revision,'citizen_aggregates':prepare_aggregates(db,revision)}


@pytest.mark.parametrize('result_kind', ['approved', 'candidate', 'missing_audit', 'wrong_stage',
                                         'wrong_version', 'inconsistent_approval', 'changed_audit'])
def test_training_persistence_uses_the_shared_approval_policy(postgres_test_session,tmp_path,monkeypatch,result_kind):
    """Synthetic child-file protocol only; never trains or registers real cases."""
    import copy,json
    from pathlib import Path
    from modules.motor_riesgo import service
    from modules.motor_riesgo.domain import digest
    db=postgres_test_session;ids=synthetic_models(db)
    original=db.get(RiskModel,__import__('uuid').UUID(ids['CONVOCATORIA']))
    artifact=copy.deepcopy(original.artifact);report=copy.deepcopy(original.report)
    artifact['version']=report['version']='synthetic-training-'+uuid4().hex
    artifact['sha256']=digest({k:v for k,v in artifact.items() if k!='sha256'})
    report['artifact_sha256']=artifact['sha256']
    if result_kind=='candidate':report['validated']=False
    elif result_kind=='missing_audit':report.pop('split_audit')
    elif result_kind=='wrong_stage':report['stage']='ADJUDICACION'
    elif result_kind=='wrong_version':report['version']='different-version'
    elif result_kind=='inconsistent_approval':report['case_interval']['passed']=False
    elif result_kind=='changed_audit':report['split_audit']['excluded_rows']=1
    report['sha256']=digest({k:v for k,v in report.items() if k!='sha256'})
    monkeypatch.setattr(service.settings,'RISK_WORK_DIR',str(tmp_path))
    (tmp_path/'synthetic.jsonl').write_bytes(b'')
    job_id=uuid4();calls=[]
    def fake_child(_interpreter,args):
        output=Path(args[args.index('--output')+1]);frozen=json.loads((output.parent/'inputs.json').read_text())
        value={'inputs':{'observations_sha256':frozen['dataset_sha256'],'observations_file_sha256':frozen['dataset_file_sha256'],
                         'cases_sha256':frozen['cases_sha256'],'feature_evidence_sha256':frozen['feature_evidence_sha256']},
               'stages':{'CONVOCATORIA':{'artifact':artifact,'report':report,'coverage':{'synthetic_only':True}}},
               'inventory':{'synthetic_only':True,'eligible_cases':0},'feature_evidence':{'synthetic_only':True}}
        output.write_text(json.dumps(value),encoding='utf-8');calls.append(True)
    monkeypatch.setattr(service,'run_process',fake_child)
    before=db.query(RiskModel).count()
    if result_kind in {'approved','candidate'}:
        result=service.train_job(db,'synthetic.jsonl',job_id)
        stored=db.get(RiskModel,__import__('uuid').UUID(result['models']['CONVOCATORIA']))
        assert stored.validated is (result_kind=='approved')
        assert db.query(RiskModel).count()==before+1
        # A resumed result is checked again and neither refits nor duplicates it.
        assert service.train_job(db,'synthetic.jsonl',job_id)['models']==result['models']
        assert len(calls)==1 and db.query(RiskModel).count()==before+1
    else:
        with pytest.raises(ValueError):service.train_job(db,'synthetic.jsonl',job_id)
        assert db.query(RiskModel).count()==before


def test_complete_cut_switch_is_atomic_and_incomplete_cut_does_not_replace_it(postgres_test_session):
    db=postgres_test_session;src=source(db);raw,_=row(db,src,1,date(2015,1,1))
    ids=synthetic_models(db)
    pointer=db.query(RiskPublication).filter_by(id=1).one();pointer.model_ids=ids
    from modules.motor_riesgo.publication import checkpoint
    cut=RiskCut(id=uuid4(),status='VALIDADO',context={'model_ids':ids,'counts':{'CONVOCATORIA':1,'ADJUDICACION':0},'day':'2026-10-16','data_cut_at':'2026-10-16T08:00:00+00:00',**citizen_context(db)})
    db.add(cut);db.flush();db.add(RiskResult(cut_id=cut.id,raw_secop_id=raw.id,stage='CONVOCATORIA',result={'index':50}))
    db.flush();assert pointer.cut_id is None
    publish(db,cut.id,actor='synthetic-isolated-test')
    assert db.get(RiskPublication,1).cut_id==cut.id
    incomplete=RiskCut(id=uuid4(),status='VALIDADO',context={**cut.context,'counts':{'CONVOCATORIA':2,'ADJUDICACION':0}})
    db.add(incomplete);db.flush()
    with pytest.raises(ValueError,match='incompleta'):
        publish(db,incomplete.id)
    assert db.get(RiskPublication,1).cut_id==cut.id


@pytest.mark.parametrize('tamper', ['report', 'runtime'])
def test_changed_evaluation_report_cannot_activate(postgres_test_session,tamper):
    db=postgres_test_session;ids=synthetic_models(db)
    model=db.get(RiskModel,__import__('uuid').UUID(ids['ADJUDICACION']))
    if tamper=='report':
        model.report={**model.report,'validated':False}
    else:
        from modules.motor_riesgo.domain import digest
        changed={**model.report,'runtime_manifest':{'changed':True}}
        changed['sha256']=digest({k:v for k,v in changed.items() if k!='sha256'})
        model.report=changed
    db.flush()
    with pytest.raises(ValueError,match='Integridad'):
        activate(db,ids,1,True)
    assert db.get(RiskPublication,1).daily_enabled is False


@pytest.mark.parametrize('tamper', ['dataset','physical_evidence','lower_bool','lower_zero','case_bool','method','repetitions','sizes',
                                  'audit_missing','audit_hash','audit_excluded','audit_policy','audit_cutoff','cases_exceed_rows',
                                  'baseline_partial','baseline_flag','baseline_total','baseline_missing','baseline_policy',
                                  'baseline_digest','baseline_boolean'])
def test_shared_approval_rejects_rehashed_but_insufficient_reports(postgres_test_session,tamper):
    from modules.motor_riesgo.domain import digest
    from analytics_ml.approval import validate_approval
    db=postgres_test_session;ids=synthetic_models(db)
    model=db.get(RiskModel,__import__('uuid').UUID(ids['CONVOCATORIA']))
    import copy
    report=copy.deepcopy(model.report);artifact=copy.deepcopy(model.artifact)
    if tamper=='dataset':
        artifact.pop('dataset_sha256');report.pop('dataset_sha256')
    elif tamper=='physical_evidence': report['feature_evidence']['registry_sha256']='invalid'
    elif tamper=='lower_bool': report['case_interval']['lower95']=True
    elif tamper=='lower_zero': report['case_interval']['lower95']=0
    elif tamper=='case_bool': report['unseen_suppliers']['cases']=True
    elif tamper=='method': report['case_interval']['method']='unsupported'
    elif tamper=='repetitions': report['case_interval']['repetitions']=1
    elif tamper=='sizes': report['split_sizes']=[1,1,1]
    elif tamper=='audit_missing': report.pop('split_audit')
    elif tamper=='audit_hash': artifact['split_audit_sha256']='a'*64
    elif tamper=='audit_excluded': report['split_audit']['excluded_rows']=1
    elif tamper=='audit_policy': report['split_audit']['policy']='unreviewed'
    elif tamper=='audit_cutoff': report['split_audit']['label_cutoffs'][0]='2099-01-01T00:00:00Z'
    elif tamper=='cases_exceed_rows': report['split_case_counts']=[6,5,5]
    elif tamper in {'baseline_partial','baseline_flag','baseline_total'}:
        report['baseline_coverage']={'policy':'binary-family-coverage-v1','complete_rows':report['split_sizes'][2],
                                     'total_rows':report['split_sizes'][2],
                                     'operation_coverage_sha256':digest({'synthetic_coverage_fixture':True})}
        report['baseline_complete_for_comparison']=True
        if tamper=='baseline_partial':report['baseline_coverage']['complete_rows']=0
        elif tamper=='baseline_flag':report['baseline_complete_for_comparison']=False
        else:report['baseline_coverage']['total_rows']=0
    elif tamper=='baseline_missing':report.pop('baseline_coverage')
    elif tamper=='baseline_policy':report['baseline_coverage']['policy']='unknown'
    elif tamper=='baseline_digest':report['baseline_coverage']['operation_coverage_sha256']='invalid'
    elif tamper=='baseline_boolean':report['baseline_coverage']['complete_rows']=True
    artifact['sha256']=digest({k:v for k,v in artifact.items() if k!='sha256'})
    report['artifact_sha256']=artifact['sha256'];report['sha256']=digest({k:v for k,v in report.items() if k!='sha256'})
    with pytest.raises(ValueError): validate_approval(artifact,report,'CONVOCATORIA',model.version,True)


def test_public_reads_can_pin_a_previous_published_cut_and_reject_drafts(postgres_test_session):
    db=postgres_test_session;src=source(db);raw,_=row(db,src,1,date(2026,1,1))
    old=RiskCut(id=uuid4(),status='PUBLICADO',context={'counts':{'CONVOCATORIA':1,'ADJUDICACION':0}})
    new=RiskCut(id=uuid4(),status='PUBLICADO',context={'counts':{'CONVOCATORIA':1,'ADJUDICACION':0}})
    draft=RiskCut(id=uuid4(),status='VALIDADO',context={'counts':{'CONVOCATORIA':0,'ADJUDICACION':0}})
    db.add_all([old,new,draft]);db.flush()
    from modules.motor_riesgo.models import CitizenSnapshot,CitizenPublication
    from modules.motor_riesgo.publication import checkpoint
    revision=checkpoint(db)
    for cut in (old,new):
        db.add(CitizenSnapshot(id=cut.id,revision=revision,risk_cut_id=cut.id,data_cut_at='2026-10-01'))
    db.flush();db.add(CitizenPublication(id=1,snapshot_id=new.id));db.flush()
    for cut,score in ((old,10),(new,90)):
        db.add(RiskResult(cut_id=cut.id,raw_secop_id=raw.id,stage='CONVOCATORIA',result={'index':score}))
    db.get(RiskPublication,1).cut_id=new.id;db.flush()
    app.dependency_overrides[get_db]=lambda:db
    try:
        with TestClient(app) as client:
            assert client.get('/api/riesgo/resultados').json()['items'][0]['result']['index']==90
            pinned=client.get('/api/riesgo/resultados',params={'cut_id':str(old.id)}).json()
            assert pinned['cut_id']==str(old.id) and pinned['total']==1 and pinned['items'][0]['result']['index']==10
            assert client.get('/api/riesgo/resultados',params={'cut_id':str(draft.id)}).status_code==404
            assert client.get('/api/riesgo/resultados',params={'cut_id':str(uuid4())}).status_code==404
    finally:
        app.dependency_overrides.pop(get_db,None)


@pytest.mark.parametrize('reviewed',[True,False])
def test_daily_pipeline_resumes_child_cursor_then_publishes_complete_cut(postgres_test_session,tmp_path,monkeypatch,reviewed):
    import os
    from core.config import settings
    from modules.jobs.model import BackgroundJob
    from modules.motor_riesgo.pipeline import update_job
    interpreter=os.environ.get('TEST_ML_INFERENCE_PYTHON')
    if not interpreter:
        pytest.skip('TEST_ML_INFERENCE_PYTHON explícito requerido')
    db=postgres_test_session;src=source(db);src.activo=True
    raw,_=row(db,src,1,date(2015,1,1));ids=synthetic_models(db)
    pointer=db.get(RiskPublication,1);pointer.model_ids=ids;pointer.daily_enabled=True;db.flush()
    monkeypatch.setattr(settings,'RISK_WORK_DIR',str(tmp_path))
    monkeypatch.setattr(settings,'RISK_INFERENCE_PYTHON',interpreter)
    if reviewed:
        from test_risk_feature_evidence import reviewed_record
        from test_risk_engine import observation
        from modules.motor_riesgo.service import register_feature_evidence
        from modules.auth.model.Admin import Admin
        admin=Admin(username='stage-'+uuid4().hex,email=uuid4().hex+'@example.test',hashed_password='synthetic-unused')
        db.add(admin);db.flush()
        item=observation(raw_secop_id=raw.id,source_id=src.id,source_row_id=raw.socrata_row_id,
            process_id=raw.id_del_proceso,prediction_at=raw.fecha_de_publicacion_del.isoformat())
        for field in item['fields'].values():field['available_at']=item['prediction_at']
        record=reviewed_record(tmp_path/'evidence',item)
        register_feature_evidence(db,record,admin.id)
    public=uuid4();payload={'day':'2026-10-16','source_ids':[src.id],'model_ids':ids}
    first=update_job(db,1,public,payload);cut_id=__import__('uuid').UUID(first['cut_id'])
    first_child=db.query(BackgroundJob).filter_by(public_id=__import__('uuid').UUID(first['waiting_for'])).one()
    # Polling the same durable step cannot create a second ingestion.
    assert update_job(db,1,public,payload)['waiting_for']==first['waiting_for']
    first_child.status='EXITOSO';first_child.active=False;first_child.result={'parcial':True,'checkpoint':{'last_id':'50'}};db.flush()
    second=update_job(db,1,public,payload)
    assert second['waiting_for']!=first['waiting_for']
    second_child=db.query(BackgroundJob).filter_by(public_id=__import__('uuid').UUID(second['waiting_for'])).one()
    second_child.status='EXITOSO';second_child.active=False;second_child.result={'parcial':False};db.flush()
    normalized=update_job(db,1,public,payload)
    transform=db.query(BackgroundJob).filter_by(public_id=__import__('uuid').UUID(normalized['waiting_for'])).one()
    assert transform.kind=='REPROCESAMIENTO'
    transform.status='EXITOSO';transform.active=False;transform.result={};db.flush()
    calls=[]
    if reviewed:
        from modules.motor_riesgo import service,result_store
        actual_process=service.run_process;actual_persist=result_store.persist_results
        def record_process(*args,**kwargs):
            calls.append('inference');return actual_process(*args,**kwargs)
        interrupted=[]
        def interrupt_after_confirmed_batch(*args,**kwargs):
            result=actual_persist(*args,**kwargs)
            if not interrupted:
                interrupted.append(True)
                raise RuntimeError('synthetic crash after committed result checkpoint')
            return result
        monkeypatch.setattr(service,'run_process',record_process)
        monkeypatch.setattr(result_store,'persist_results',interrupt_after_confirmed_batch)
        with pytest.raises(RuntimeError,match='committed result checkpoint'):
            update_job(db,1,public,payload)
        assert db.get(RiskCut,cut_id).context['persistence_checkpoint']['lines']==1
        assert db.query(RiskResult).count()==1 and db.get(RiskPublication,1).cut_id is None
    result=update_job(db,1,public,payload)
    if not reviewed:
        assert result['daily_paused'] is True and 'temporal' in result['blocked']
        assert db.get(RiskPublication,1).cut_id is None and db.query(RiskResult).count()==0
        assert db.get(RiskCut,cut_id).status=='BLOQUEADO'
        return
    assert result['status']=='PUBLICADO'
    assert result['counts']=={'CONVOCATORIA':1,'ADJUDICACION':0}
    assert db.get(RiskPublication,1).cut_id==cut_id
    assert calls==['inference']
    assert update_job(db,1,public,payload)['resumed'] is True


def test_failed_child_pauses_daily_without_publishing(postgres_test_session,tmp_path,monkeypatch):
    from core.config import settings
    from modules.jobs.model import BackgroundJob
    from modules.motor_riesgo.pipeline import update_job
    db=postgres_test_session;src=source(db);src.activo=True;ids=synthetic_models(db)
    pointer=db.get(RiskPublication,1);pointer.model_ids=ids;pointer.daily_enabled=True;db.flush()
    monkeypatch.setattr(settings,'RISK_WORK_DIR',str(tmp_path))
    public=uuid4();payload={'day':'2026-10-16','source_ids':[src.id],'model_ids':ids}
    first=update_job(db,1,public,payload)
    child=db.query(BackgroundJob).filter_by(public_id=__import__('uuid').UUID(first['waiting_for'])).one()
    child.status='ERROR';child.active=False;db.flush()
    result=update_job(db,1,public,payload)
    assert result['daily_paused'] is True
    assert pointer.daily_enabled is False and pointer.cut_id is None
