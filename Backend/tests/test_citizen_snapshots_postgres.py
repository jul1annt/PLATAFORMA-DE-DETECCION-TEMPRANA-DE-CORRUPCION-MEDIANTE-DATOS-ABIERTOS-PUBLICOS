"""Exact snapshot reads across mutable ingestion/normalization and rollback."""
from datetime import date,datetime,timezone
from uuid import uuid4
import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient
from main import app
from core.database import get_db
from modules.motor_riesgo.publication import initialize_baseline,checkpoint,read_snapshot,restore_snapshot
from modules.motor_riesgo.models import CitizenPublication,CitizenSnapshot,RiskPublication,RiskCut,RiskResult
from modules.motor_riesgo.service import publish
from modules.transformacion.repository.transformacion import TransformacionRepository
from modules.transformacion.model.ContratoAnomaloIncompleto import ContratoAnomaloIncompleto
from modules.transformacion.model.EstadisticaCamposFaltantes import EstadisticaCamposFaltantes
from test_risk_engine_postgres import source,row,synthetic_models,citizen_context


def test_before_images_preserve_edits_inserts_deletes_and_summary_without_cloning(postgres_test_session):
    db=postgres_test_session;src=source(db);raw,cp=row(db,src,1,date(2020,1,1),amount=100,incomplete=True)
    original_id=cp.id
    baseline=initialize_baseline(db,'2026-10-01');identifier=baseline.id
    assert db.execute(text('SELECT count(*) FROM riesgo_historial.contratos_procesados WHERE id=:id'),{'id':original_id}).scalar_one()==0
    cp.valor_total_normalizado=999;cp.es_incompleto=False;db.flush()
    _,second=row(db,src,2,date(2020,1,2),amount=200)
    # Multiple versions of the same ID occupy nonoverlapping ranges.
    cp.valor_total_normalizado=888;db.flush()
    db.delete(cp);db.flush()
    with read_snapshot(db,identifier):
        repo=TransformacionRepository(db)
        record=repo.get_contrato_by_id(original_id)
        assert record.valor_total_normalizado==100 and record.es_incompleto is True
        assert repo.get_contrato_by_id(second.id) is None
        assert repo.get_dashboard_metricas()['total_contratos']==1
        assert repo.get_dashboard_metricas()['total_incompletos']==1
    assert TransformacionRepository(db).get_contrato_by_id(original_id) is None
    assert TransformacionRepository(db).get_dashboard_metricas()['total_contratos']==1
    assert TransformacionRepository(db).get_dashboard_metricas()['total_incompletos']==0
    assert db.execute(text('SELECT count(*) FROM riesgo_historial.contratos_procesados WHERE id=:id'),{'id':original_id}).scalar_one()==3


def test_quality_findings_and_field_statistics_use_the_same_revision(postgres_test_session):
    db=postgres_test_session;src=source(db);raw,cp=row(db,src,1,date(2020,1,1),incomplete=True)
    finding=ContratoAnomaloIncompleto(raw_secop_id=raw.id,id_contrato_procesado=cp.id,
        motivo='CAMPO_FALTANTE',tipo_anomalia='CAMPO_FALTANTE',campo_afectado='documento',descripcion='Antes')
    statistic=EstadisticaCamposFaltantes(nombre_campo='documento',contador_faltantes=1,porcentaje_total=100)
    db.add_all([finding,statistic]);db.flush()
    baseline=initialize_baseline(db,'2026-10-01');identifier=baseline.id
    finding.descripcion='Después';statistic.contador_faltantes=0;db.flush()
    with read_snapshot(db,identifier):
        assert db.query(ContratoAnomaloIncompleto).one().descripcion=='Antes'
        assert TransformacionRepository(db).get_all_estadisticas()[0].contador_faltantes==1
    assert db.query(ContratoAnomaloIncompleto).one().descripcion=='Después'


def test_public_calls_and_risk_pointer_switch_together_and_old_cut_can_be_pinned(postgres_test_session):
    db=postgres_test_session;src=source(db);raw,cp=row(db,src,1,date(2020,1,1),amount=100)
    identifier=cp.id;ids=synthetic_models(db);baseline_id=db.get(CitizenPublication,1).snapshot_id
    db.get(RiskPublication,1).model_ids=ids;db.flush()
    cp.valor_total_normalizado=200;db.flush()
    cut=RiskCut(id=uuid4(),status='VALIDADO',context={'model_ids':ids,'counts':{'CONVOCATORIA':1,'ADJUDICACION':0},
        'day':'2026-10-16','data_cut_at':'2026-10-16T12:00:00+00:00',**citizen_context(db)})
    db.add(cut);db.flush();db.add(RiskResult(cut_id=cut.id,raw_secop_id=raw.id,stage='CONVOCATORIA',result={'index':70}))
    db.flush()
    app.dependency_overrides[get_db]=lambda:db
    try:
        with TestClient(app) as client:
            before=client.get(f'/api/procesados/{identifier}')
            assert before.status_code==200 and float(before.json()['valor_total_normalizado'])==100
            assert before.headers['x-public-cut']==str(baseline_id)
            assert client.get('/api/riesgo/estado').json()['available'] is False
            publish(db,cut.id)
            after=client.get(f'/api/procesados/{identifier}')
            assert float(after.json()['valor_total_normalizado'])==200 and after.headers['x-public-cut']==str(cut.id)
            assert client.get('/api/riesgo/estado').json()['cut_id']==str(cut.id)
            old_headers={'X-Public-Cut':str(baseline_id)}
            assert float(client.get(f'/api/procesados/{identifier}',headers=old_headers).json()['valor_total_normalizado'])==100
            assert client.get('/api/riesgo/estado',headers=old_headers).json()['available'] is False
            assert client.get('/api/riesgo/resultados',params={'cut_id':str(cut.id)},headers=old_headers).status_code==409
            assert client.get(f'/api/procesados/{identifier}',headers={'X-Public-Cut':str(uuid4())}).status_code==404
            assert client.get(f'/api/procesados/{identifier}',headers={'X-Public-Cut':'invalid'}).status_code==422
    finally: app.dependency_overrides.pop(get_db,None)


def test_changed_quality_only_cannot_publish_a_stale_checkpoint(postgres_test_session):
    db=postgres_test_session;src=source(db);raw,cp=row(db,src,1,date(2020,1,1));ids=synthetic_models(db)
    db.get(RiskPublication,1).model_ids=ids;db.flush()
    revision=checkpoint(db)
    db.add(EstadisticaCamposFaltantes(nombre_campo='otro',contador_faltantes=1,porcentaje_total=100));db.flush()
    cut=RiskCut(id=uuid4(),status='VALIDADO',context={'model_ids':ids,'counts':{'CONVOCATORIA':1,'ADJUDICACION':0},
        'day':'2026-10-16','data_cut_at':'2026-10-16T12:00:00Z','citizen_revision':revision})
    db.add(cut);db.flush();db.add(RiskResult(cut_id=cut.id,raw_secop_id=raw.id,stage='CONVOCATORIA',result={'index':70}));db.flush()
    baseline=db.get(CitizenPublication,1).snapshot_id
    with pytest.raises(ValueError,match='ciudadanos cambiaron'): publish(db,cut.id)
    assert db.get(RiskPublication,1).cut_id is None and db.get(CitizenPublication,1).snapshot_id==baseline


def test_all_abstentions_do_not_replace_a_valid_citizen_cut(postgres_test_session):
    db=postgres_test_session;src=source(db);raw,_=row(db,src,1,date(2020,1,1));ids=synthetic_models(db)
    db.get(RiskPublication,1).model_ids=ids;db.flush()
    baseline=db.get(CitizenPublication,1).snapshot_id
    cut=RiskCut(id=uuid4(),status='VALIDADO',context={'model_ids':ids,'counts':{'CONVOCATORIA':1,'ADJUDICACION':0},
        'day':'2026-10-16','data_cut_at':'2026-10-16T12:00:00Z',**citizen_context(db)})
    db.add(cut);db.flush();db.add(RiskResult(cut_id=cut.id,raw_secop_id=raw.id,stage='CONVOCATORIA',result={'index':None}));db.flush()
    with pytest.raises(ValueError,match='temporal evaluable'):publish(db,cut.id)
    assert db.get(CitizenPublication,1).snapshot_id==baseline and db.get(RiskPublication,1).cut_id is None


def test_invoker_trigger_permissions_cover_history_views_and_sequences(postgres_test_session):
    from modules.motor_riesgo.runtime_permissions import missing_runtime_permissions
    assert missing_runtime_permissions(postgres_test_session)==[]


def test_public_read_configuration_is_restored_after_errors(postgres_test_session):
    db=postgres_test_session;src=source(db);row(db,src,1,date(2020,1,1))
    baseline=initialize_baseline(db,'2026-10-01')
    original=db.execute(text('SHOW search_path')).scalar_one()
    with pytest.raises(RuntimeError):
        with read_snapshot(db,baseline.id):
            assert db.info['public_snapshot']['id']==str(baseline.id)
            assert db.execute(text('SHOW search_path')).scalar_one()=='riesgo_ciudadano,public'
            raise RuntimeError('synthetic interruption')
    assert 'public_snapshot' not in db.info
    assert db.execute(text('SHOW search_path')).scalar_one()==original


def test_queued_and_synchronous_exports_keep_the_requested_revision(postgres_test_session,tmp_path,monkeypatch):
    from modules.jobs.model import BackgroundJob
    from modules.transformacion.services.export_service import generate_contract_export
    from shared.export_artifacts import result_artifact_path
    from uuid import UUID
    db=postgres_test_session;src=source(db);raw,cp=row(db,src,1,date(2020,1,1),amount=123)
    baseline=initialize_baseline(db,'2026-10-01');identifier=baseline.id
    cp.valor_total_normalizado=999;db.flush()
    monkeypatch.setattr('shared.export_artifacts.settings.EXPORT_ARTIFACT_DIR',str(tmp_path))
    app.dependency_overrides[get_db]=lambda:db
    try:
        with TestClient(app) as client:
            headers={'X-Public-Cut':str(identifier)}
            response=client.post('/api/procesados/export/csv/jobs',headers=headers)
            assert response.status_code==202,response.text
            public_id=UUID(response.json()['id'])
            job=db.query(BackgroundJob).filter_by(public_id=public_id).one()
            assert job.payload['public_cut_id']==str(identifier)
            result=generate_contract_export(db,public_id,job.payload)
            assert result['public_cut_id']==str(identifier)
            assert b'123' in result_artifact_path(public_id,result).read_bytes()
            assert b'999' not in result_artifact_path(public_id,result).read_bytes()
            synchronous=client.get('/api/procesados/export/csv',headers=headers)
            assert synchronous.status_code==200 and synchronous.headers['x-public-cut']==str(identifier)
            assert b'123' in synchronous.content and b'999' not in synchronous.content
    finally: app.dependency_overrides.pop(get_db,None)


def test_publication_failure_rolls_back_both_pointers_and_new_snapshot(postgres_test_session,monkeypatch):
    from modules.motor_riesgo import service
    db=postgres_test_session;src=source(db);raw,cp=row(db,src,1,date(2020,1,1));ids=synthetic_models(db)
    db.get(RiskPublication,1).model_ids=ids;db.flush()
    baseline=db.get(CitizenPublication,1).snapshot_id
    cut=RiskCut(id=uuid4(),status='VALIDADO',context={'model_ids':ids,'counts':{'CONVOCATORIA':1,'ADJUDICACION':0},
        'day':'2026-10-16','data_cut_at':'2026-10-16T12:00:00Z',**citizen_context(db)})
    db.add(cut);db.flush();cut_id=cut.id
    db.add(RiskResult(cut_id=cut.id,raw_secop_id=raw.id,stage='CONVOCATORIA',result={'index':70}));db.flush()
    def interrupted(*args,**kwargs): raise RuntimeError('synthetic failure after pointer assignment')
    monkeypatch.setattr(service,'audit',interrupted)
    with pytest.raises(RuntimeError):
        with db.begin_nested(): service.publish(db,cut_id)
    assert db.get(CitizenPublication,1).snapshot_id==baseline
    assert db.get(RiskPublication,1).cut_id is None
    assert db.get(CitizenSnapshot,cut_id) is None
    assert db.get(RiskCut,cut_id).status=='VALIDADO'


@pytest.mark.parametrize('tamper',[None,'artifact','report','certificate','aggregate'])
def test_restore_preserves_historical_data_after_feature_upgrade_and_rejects_tampering(postgres_test_session,monkeypatch,tamper):
    from copy import deepcopy
    from types import SimpleNamespace
    from modules.motor_riesgo.models import RiskModel
    from modules.motor_riesgo.service import checked_models
    from gateway.middlewares.auth_middleware import get_current_admin
    db=postgres_test_session;src=source(db);raw,cp=row(db,src,1,date(2020,1,1),amount=100)
    identifier=cp.id;ids=synthetic_models(db);pointer=db.get(RiskPublication,1);pointer.model_ids=ids
    cuts=[]
    for amount,index in [(100,10),(200,90)]:
        cp.valor_total_normalizado=amount;db.flush()
        cut=RiskCut(id=uuid4(),status='VALIDADO',context={'model_ids':ids,'counts':{'CONVOCATORIA':1,'ADJUDICACION':0},
            'day':'2026-10-16','data_cut_at':'2026-10-16T12:00:00Z',**citizen_context(db)})
        db.add(cut);db.flush();db.add(RiskResult(cut_id=cut.id,raw_secop_id=raw.id,stage='CONVOCATORIA',result={'index':index}));db.flush()
        publish(db,cut.id);cuts.append(cut.id)
    # New training/inference must reject old feature versions; serving an
    # already approved immutable cut must not execute any historical estimator.
    monkeypatch.setattr('analytics_ml.inference.FEATURE_VERSION','future-incompatible-fixture')
    with pytest.raises(ValueError):checked_models(db,ids)
    from uuid import UUID
    model=db.get(RiskModel,UUID(ids['CONVOCATORIA']))
    if tamper in ('artifact','report'):
        value=deepcopy(getattr(model,tamper));value['version']='modified';setattr(model,tamper,value)
    elif tamper=='certificate':
        first=db.get(RiskCut,cuts[0]);value=deepcopy(first.context)
        value['approval_certificate']['CONVOCATORIA']['feature_version']='modified';first.context=value
    elif tamper=='aggregate':db.get(CitizenSnapshot,cuts[0]).aggregates=None
    db.flush()
    app.dependency_overrides[get_db]=lambda:db
    app.dependency_overrides[get_current_admin]=lambda:SimpleNamespace(id=1)
    try:
        with TestClient(app) as client:
            response=client.post('/api/riesgo/admin/revertir/'+str(cuts[0]))
            if tamper:
                assert response.status_code==409,response.text
                assert db.get(CitizenPublication,1).snapshot_id==cuts[1]
                assert db.get(RiskPublication,1).cut_id==cuts[1]
            else:
                assert response.status_code==200,response.text
                assert response.json()['daily_enabled'] is False
                assert float(client.get(f'/api/procesados/{identifier}').json()['valor_total_normalizado'])==100
                assert client.get('/api/riesgo/resultados').json()['items'][0]['result']['index']==10
                assert db.get(CitizenPublication,1).snapshot_id==cuts[0]
                assert db.get(RiskPublication,1).cut_id==cuts[0]
    finally:
        app.dependency_overrides.pop(get_db,None);app.dependency_overrides.pop(get_current_admin,None)


def test_public_readers_keep_the_cut_during_real_committed_writes(postgres_test_session):
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from modules.ingesta.model.FuenteDatos import FuenteDatos
    from modules.ingesta.model.RawSecop import RawSecop
    from modules.transformacion.model.ContratoProcesado import ContratoProcesado
    from citizen_history_fixture import OwnedCitizenHistory
    engine=create_engine(postgres_test_session.connection().engine.url,pool_size=3,max_overflow=0)
    owned=OwnedCitizenHistory(engine);raw_id=snapshot_id=cp_id=source_id=None
    try:
        with Session(engine) as db:
            src=source(db);raw,cp=row(db,src,1,date(2020,1,1),amount=100)
            source_id,raw_id,cp_id=src.id,raw.id,cp.id
            snapshot_id=initialize_baseline(db,'2026-10-01').id
            db.commit()
        def writer():
            for amount in range(200,208):
                with engine.begin() as db:
                    db.execute(text('UPDATE public.contratos_procesados SET valor_total_normalizado=:value WHERE id=:id'),{'value':amount,'id':cp_id})
        def reader():
            values=[]
            for _ in range(24):
                with Session(engine) as db:
                    with read_snapshot(db,snapshot_id):
                        values.append(TransformacionRepository(db).get_contrato_by_id(cp_id).valor_total_normalizado)
            return values
        with ThreadPoolExecutor(max_workers=3) as pool:
            readers=[pool.submit(reader),pool.submit(reader)];writing=pool.submit(writer)
            writing.result(timeout=30)
            assert all(value==100 for future in readers for value in future.result(timeout=30))
        with engine.connect() as db:
            assert db.execute(text('SELECT valor_total_normalizado FROM public.contratos_procesados WHERE id=:id'),{'id':cp_id}).scalar_one()==207
    finally:
        with engine.begin() as db:
            if snapshot_id:
                db.execute(text('DELETE FROM riesgo_publicacion_ciudadana WHERE id=1 AND snapshot_id=:id'),{'id':snapshot_id})
                db.execute(text('DELETE FROM riesgo_cortes_ciudadanos WHERE id=:id AND risk_cut_id IS NULL'),{'id':snapshot_id})
            if cp_id: db.execute(text('DELETE FROM public.contratos_procesados WHERE id=:id'),{'id':cp_id})
            if raw_id: db.execute(text('DELETE FROM public.raw_secop WHERE id=:id'),{'id':raw_id})
            if source_id: db.execute(text('DELETE FROM public.fuentes_datos WHERE id=:id'),{'id':source_id})
        owned.cleanup([raw_id] if raw_id else [])
        engine.dispose()


@pytest.mark.parametrize('order',['asc','desc'])
@pytest.mark.parametrize('sort',[None,'fecha','valor','precio_base_normalizado','entidad','proveedor','riesgo','id'])
def test_bounded_snapshot_pages_equal_the_full_view_with_nulls_ties_and_filters(postgres_test_session,sort,order):
    from modules.transformacion.domain.filters import ContratoProcesadoFilter
    from modules.transformacion.model.ContratoProcesado import ContratoProcesado as C
    db=postgres_test_session;src=source(db);contracts=[]
    for i in range(45):
        _,cp=row(db,src,i,date(2020,1,1+(i%3)),amount=i%4*10,incomplete=i%2==0)
        cp.fecha_publicacion_normalizada=None if i%8==0 else cp.fecha_publicacion_normalizada
        cp.valor_total_normalizado=None if i%6==0 else cp.valor_total_normalizado
        cp.precio_base_normalizado=None if i%7==0 else cp.precio_base_normalizado
        cp.entidad_normalizada='Entidad '+str(i%5);cp.proveedor_normalizado='Nombre '+str(i%7)
        cp.nivel_confianza=i%3*10;contracts.append(cp)
    db.flush();baseline=initialize_baseline(db,'2026-10-01');selected=baseline.id
    for cp in contracts[:10]:cp.valor_total_normalizado=999;cp.entidad_normalizada='Actualizada'
    for cp in contracts[-5:]:db.delete(cp)
    db.flush()
    for i in range(100,105):row(db,src,i,date(2021,1,1),amount=900)
    with read_snapshot(db,selected):
        repo=TransformacionRepository(db)
        for filters in (ContratoProcesadoFilter(),ContratoProcesadoFilter(solo_incompletos=True),
                        ContratoProcesadoFilter(valor_min=0,valor_max=10),ContratoProcesadoFilter(valor_max=0),
                        ContratoProcesadoFilter(proveedor='Nombre 1')):
            oracle=repo._ordered_contracts(repo._filtered_contracts(C,filters),C,sort,order)
            expected=[item.id for item in oracle.all()]
            observed=[]
            for offset in range(0,len(expected)+1,7):
                page,total=repo.search_contratos(filters,skip=offset,limit=7,sort=sort,order=order)
                assert total==len(expected)
                observed.extend(item.id for item in page)
            assert observed==expected and len(set(observed))==len(observed)


def test_public_chart_reads_use_persisted_aggregates_without_grouping_source_rows(postgres_test_session):
    from sqlalchemy import event
    db=postgres_test_session;src=source(db);row(db,src,1,date(2020,1,1))
    identifier=initialize_baseline(db,'2026-10-01').id
    with read_snapshot(db,identifier):
        statements=[];bind=db.get_bind()
        def record(connection,cursor,statement,parameters,context,many):statements.append(statement)
        event.listen(bind,'before_cursor_execute',record)
        try:
            repo=TransformacionRepository(db)
            assert sum(item['value'] for item in repo.get_risk_distribution())==1
            assert repo.get_top_providers(10)[0]['contracts']==1
        finally:event.remove(bind,'before_cursor_execute',record)
        assert statements==[]


@pytest.mark.parametrize('tamper',['missing','hash','rows','revision'])
def test_invalid_aggregates_block_activation_and_expensive_public_reads(postgres_test_session,tamper):
    from copy import deepcopy
    from modules.motor_riesgo.domain import digest
    from modules.motor_riesgo.service import activate
    db=postgres_test_session;src=source(db);row(db,src,1,date(2020,1,1));ids=synthetic_models(db)
    pointer=db.get(CitizenPublication,1);snapshot=db.get(CitizenSnapshot,pointer.snapshot_id)
    value=deepcopy(snapshot.aggregates)
    if tamper=='missing':value=None
    elif tamper=='hash':value['sha256']='f'*64
    else:
        value[tamper]+=1
        value['sha256']=digest({k:v for k,v in value.items() if k!='sha256'})
    snapshot.aggregates=value;db.flush()
    with pytest.raises(ValueError):activate(db,ids,1,True)
    assert db.get(RiskPublication,1).daily_enabled is False
    app.dependency_overrides[get_db]=lambda:db
    try:
        with TestClient(app) as client:
            assert client.get('/api/procesados/metricas/distribucion-riesgo').status_code==503
            assert client.get('/api/procesados/metricas/top-proveedores').status_code==503
    finally:app.dependency_overrides.pop(get_db,None)


def test_baseline_preparation_is_authenticated_deduplicated_and_runs_in_worker(postgres_test_session):
    from types import SimpleNamespace
    from gateway.middlewares.auth_middleware import get_current_admin
    from modules.jobs.worker import _execute
    from modules.motor_riesgo.models import RiskModel
    db=postgres_test_session;src=source(db);row(db,src,1,date(2020,1,1))
    app.dependency_overrides[get_db]=lambda:db
    try:
        with TestClient(app) as client:
            assert client.post('/api/riesgo/admin/preparar-base').status_code in (401,403)
            app.dependency_overrides[get_current_admin]=lambda:SimpleNamespace(id=1)
            first=client.post('/api/riesgo/admin/preparar-base');second=client.post('/api/riesgo/admin/preparar-base')
            assert first.status_code==second.status_code==202 and first.json()['id']==second.json()['id']
            assert db.get(CitizenPublication,1) is None
            from uuid import UUID
            result=_execute('RIESGO_BASE_CIUDADANA',{},job_public_id=UUID(first.json()['id']),work_db=db)
            assert result['aggregates_ready'] is True
            assert db.query(RiskModel).count()==0 and db.get(RiskPublication,1).daily_enabled is False
            assert db.get(CitizenSnapshot,db.get(CitizenPublication,1).snapshot_id).aggregates['rows']==1
            assert _execute('RIESGO_BASE_CIUDADANA',{},job_public_id=UUID(first.json()['id']),work_db=db)==result
            assert db.query(CitizenSnapshot).count()==1
    finally:
        app.dependency_overrides.pop(get_db,None);app.dependency_overrides.pop(get_current_admin,None)


def test_initial_pointer_waits_for_complete_aggregates_and_preserves_its_original_revision(postgres_test_session):
    db=postgres_test_session;src=source(db);raw,cp=row(db,src,1,date(2020,1,1),amount=100)
    identifier=uuid4()
    initial=initialize_baseline(db,'2026-10-01',compute_aggregates=False,snapshot_id=identifier)
    assert initial.aggregates is None and db.get(CitizenPublication,1) is None
    cp.valor_total_normalizado=200;cp.nit_proveedor_clave='900000002';db.flush()
    ready=initialize_baseline(db,'2026-10-01',snapshot_id=identifier)
    assert ready.id==identifier and db.get(CitizenPublication,1).snapshot_id==identifier
    assert ready.aggregates['top_providers'][0]['nit']=='900000001'
    with read_snapshot(db,identifier):
        assert TransformacionRepository(db).get_contrato_by_id(cp.id).valor_total_normalizado==100
