"""Synthetic engineering checks never supply labels to the operational corpus."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import subprocess
import sys
from uuid import uuid4
import pytest
from modules.motor_riesgo.domain import NUMERIC, CATEGORICAL, FEATURE_VERSION, PREDICTION_POLICY, digest, eligible_case, features, percentile
from modules.motor_riesgo.rules import iqr_finding, rolling_context
from analytics_ml.corpus import verified_cases, prepare_rows
from analytics_ml.evaluation import temporal_split, hit_weights, paired_case_interval
from analytics_ml.inference import validate_artifact, predict


@pytest.mark.parametrize('example', json.loads((Path(__file__).parent/'fixtures/secop_links.json').read_text(encoding='utf-8')))
def test_official_source_links_preserve_valid_urls_and_reject_unsafe_destinations(example):
    from modules.motor_riesgo.domain import secop_source_url
    assert secop_source_url(example['input'])==example['expected']


def observation(stage='CONVOCATORIA', **changes):
    at = '2020-01-01T00:00:00+00:00'
    fields = {n: {'value': 1., 'sha256': 'a'*64, 'available_at': at} for n in NUMERIC[stage]}
    fields.update({n: {'value': 'X', 'sha256': 'a'*64, 'available_at': at} for n in CATEGORICAL})
    return {'stage': stage, 'source_id': 1, 'source_row_id': 'ROW1', 'process_id': 'P1', 'award_id': 'AWARD1' if stage == 'ADJUDICACION' else None,
            'prediction_at': at, 'stage_event_at': at, 'temporal_scope': 'historical_stage_snapshot',
            'raw_secop_id': 1, 'fields': fields, **changes}


def artifact(stage='CONVOCATORIA'):
    from analytics_ml.training import fit_transform
    from analytics_ml.runtime import prediction_code_sha256
    values, _ = features(observation(stage), stage)
    transform = fit_transform([{'values': values}], stage)
    size = 2*len(NUMERIC[stage])+sum(len(transform['categories'][n])+1 for n in CATEGORICAL)
    result = {'feature_version': FEATURE_VERSION, 'prediction_policy': PREDICTION_POLICY, 'stage': stage, 'version': 'synthetic', 'transform': transform,
              'prediction_code_sha256':prediction_code_sha256(),
              'members': [{'coef': [0.]*size, 'intercept': 1.}], 'reference': [0., 1., 2.], 'positive_target': 'CORRUPCION'}
    result['sha256'] = digest(result)
    return result


@pytest.mark.parametrize('stage', ['CONVOCATORIA','ADJUDICACION'])
def test_stage_whitelist_excludes_labels_names_ids_and_future_award(stage):
    item = observation(stage)
    item['fields']['nombre_proveedor'] = {'value': 'Prohibido'}
    item['fields']['condena'] = {'value': True}
    values, reasons = features(item,stage)
    assert not reasons
    assert set(values) == set(NUMERIC[stage]) | set(CATEGORICAL)
    if stage == 'CONVOCATORIA':
        assert 'log_adjudicado' not in values


def test_future_data_rejected_and_missing_evidence_is_not_zero_risk():
    item = observation()
    item['fields']['log_presupuesto']['available_at'] = '2021-01-01T00:00:00Z'
    with pytest.raises(ValueError, match='futura'):
        features(item,'CONVOCATORIA')
    item = observation()
    del item['fields']['log_presupuesto']
    result = predict(artifact(),item)
    assert result['index'] is None and result['coverage'] < 1
    assert result['model_version']=='synthetic' and result['provenance']['process_id']=='P1'
    assert result['prediction_at']==item['prediction_at'] and result['references']


@pytest.mark.parametrize('change', [{'source_id':None}, {'process_id':'N/A'}, {'source_row_id':''}, {'stage':'ADJUDICACION'}, {'identity_ambiguous':True}])
def test_invalid_identity_abstains_even_when_all_predictors_exist(change):
    result=predict(artifact(),observation(**change))
    assert result['index'] is None and result['model_version']=='synthetic'


def test_award_requires_its_official_identity_and_distinct_awards_remain_distinct():
    assert predict(artifact('ADJUDICACION'),observation('ADJUDICACION',award_id=None))['index'] is None
    rows,coverage=prepare_rows([observation('ADJUDICACION'),observation('ADJUDICACION',source_row_id='ROW2',award_id='AWARD2')],{},'ADJUDICACION')
    assert len(rows)==2 and not coverage['excluded']


def test_distinct_source_rows_of_one_procurement_unit_are_excluded_as_ambiguous():
    rows,coverage=prepare_rows([observation(),observation(source_row_id='ROW2')],{},'CONVOCATORIA')
    assert not rows and coverage['excluded']['identidad_operacion_ambigua']==2


def test_award_label_projection_to_call_requires_explicit_reviewed_stage_link():
    case={'case_id':'C1','conduct':'CORRUPCION','published_at':'2026-01-01T00:00:00Z',
          'first_investigation_at':'2025-01-01T00:00:00Z',
          'operations':[{'source_id':1,'source_row_id':'ROW1','process_id':'P1','award_id':'AWARD1'}]}
    rows,_=prepare_rows([observation()],{'C1':case},'CONVOCATORIA')
    assert rows[0]['positive'] is False
    case['operations'][0]['stages']=['CONVOCATORIA','ADJUDICACION']
    rows,_=prepare_rows([observation()],{'C1':case},'CONVOCATORIA')
    assert rows[0]['positive'] is True


def test_case_grouping_joins_shared_judgments_and_dockets_transitively():
    from analytics_ml.corpus import case_groups
    cases={'A':{'authority':'Corte, Sala Penal','docket':'123-45','judgment':{'sha256':'a'*64}},
           'B':{'authority':'Otra autoridad','docket':'987','judgment':{'sha256':'a'*64}},
           'C':{'authority':'OTRA AUTORIDAD','docket':'9-8-7','judgment':{'sha256':'b'*64}},
           'D':{'authority':'Corte distinta','docket':'987','judgment':{'sha256':'c'*64}}}
    groups=case_groups(cases)
    assert groups['A']==groups['B']==groups['C'] and groups['D']!=groups['A']


def test_positive_without_documented_preinvestigation_cutoff_cannot_train():
    case={'case_id':'C1','conduct':'CORRUPCION','published_at':'2026-01-01T00:00:00Z',
          'operations':[{'source_id':1,'source_row_id':'ROW1','process_id':'P1'}]}
    rows,coverage=prepare_rows([observation()],{'C1':case},'CONVOCATORIA')
    assert not rows and coverage['excluded']['falta_corte_temporal_preinvestigacion']==1


def test_portable_artifact_integrity_and_ties():
    model = artifact()
    validate_artifact(model)
    assert predict(model,observation())['index'] == 50
    model['members'][0]['intercept'] += 1
    with pytest.raises(ValueError):
        validate_artifact(model)
    assert percentile([1.,1.,1.],1.) == 50
    assert hit_weights([1.,1.,1.,1.],.05) == [.05]*4
    assert hit_weights([4.,3.,2.,1.],.05) == [.2,0.,0.,0.]


@pytest.mark.parametrize('stage', ['CONVOCATORIA', 'ADJUDICACION'])
def test_sparse_inference_equals_dense_reference(stage):
    from analytics_ml.inference import PreparedPredictor,raw_score
    model=artifact(stage);values,_=features(observation(stage),stage)
    assert PreparedPredictor(model).score(values)[0]==raw_score(model,values)[0]
    assert predict(model,observation(stage),PreparedPredictor(model).score)['index']==predict(model,observation(stage))['index']
    import random
    rng=random.Random(42)
    model['members'][0]['coef']=[rng.uniform(-1,1) for _ in model['members'][0]['coef']]
    model['sha256']=digest({k:v for k,v in model.items() if k!='sha256'})
    prepared=PreparedPredictor(model)
    for i in range(20):
        values={n:None if i%3==0 else rng.uniform(0,10) for n in NUMERIC[stage]}
        values.update({n:('X' if i%2 else 'UNSEEN') for n in CATEGORICAL})
        assert prepared.score(values)[0]==raw_score(model,values)[0]


@pytest.mark.parametrize('change',[
    {'temporal_scope':None},{'temporal_scope':'observed_at_capture_not_backdated'},
    {'stage_event_at':None},{'stage_event_at':'2020-01-02T00:00:00Z'},
    {'stage_event_at':'invalid'},
])
def test_stage_models_abstain_without_an_exact_historical_landmark(change):
    result=predict(artifact(),observation(**change))
    assert result['index'] is None and result['signals']==[]
    assert any('etapa' in reason for reason in result['reasons'])


def test_artifact_with_different_prediction_policy_is_incompatible():
    model=artifact();model['prediction_policy']='current-state-fixture'
    model['sha256']=digest({k:v for k,v in model.items() if k!='sha256'})
    with pytest.raises(ValueError):validate_artifact(model)


def test_small_or_constant_iqr_is_unevaluable_and_field_missing_does_not_exclude_other_rules():
    assert iqr_finding(100,list(range(29)))['detected'] is None
    assert iqr_finding(100,[5]*30)['detected'] is None
    assert iqr_finding(1000,list(range(1,32)))['detected'] is True


def test_iqr_comparator_keeps_distinct_awards_of_the_same_process():
    from math import log1p
    from modules.motor_riesgo.rules import chronological_baseline
    history=[{'source_id':1,'process_id':'P','award_id':str(i),'prediction_at':'2026-01-01T00:00:00Z',
              'values':{'categoria':'80111600','modalidad':'DIRECTA','log_adjudicado':log1p(i+1)}} for i in range(30)]
    target={'source_id':1,'process_id':'P','award_id':'NEW','prediction_at':'2026-01-02T00:00:00Z',
            'values':{'categoria':'80111600','modalidad':'DIRECTA','log_adjudicado':log1p(1000)}}
    scores,coverage=chronological_baseline(history,[target],'ADJUDICACION')
    assert scores==[1.] and coverage['iqr_evaluable_rows']==1


def test_rolling_windows_distinct_processes_same_identity_and_no_future():
    at = datetime(2026,1,1,tzinfo=timezone.utc)
    current = {'at': at,'process_id':'NEW','supplier_key':'A','buyer_key':'B','category':'C'}
    first = {**current,'at':at-timedelta(days=5),'process_id':'OLD','direct':True}
    rows = [first, dict(first), {**first,'supplier_key':'HOMONYM'}, {**first,'at':at+timedelta(days=1)},
            {**first,'at':at-timedelta(days=100),'process_id':'TOOOLD'}]
    assert rolling_context(rows,current) == {'reiteraciones_30d':1,'directas_90d':1}


def test_candidate_and_supplier_sanction_are_never_positive_labels(tmp_path):
    candidate = {'case_id':'candidate','status':'CANDIDATO','supplier':'A','operations':[]}
    cases, inventory = verified_cases([candidate],tmp_path)
    assert not cases and inventory['eligible_cases'] == 0
    assert 'vinculo_secop_no_exacto' in eligible_case(candidate)
    rows, coverage = prepare_rows([observation()],cases,'CONVOCATORIA')
    assert rows[0]['positive'] is False and coverage['known_positive_rows'] == 0


def test_fraud_registry_is_separate_from_positive_corruption_target(tmp_path):
    record={'case_id':'fraud','conduct':'FRAUDE_CONTRACTUAL','operations':[]}
    cases,inventory=verified_cases([record],tmp_path)
    assert not cases and inventory['training_target']=='CORRUPCION'
    assert inventory['registry_by_conduct']=={'FRAUDE_CONTRACTUAL':1}
    assert 'fraude_contractual_separado_del_objetivo_corrupcion' in inventory['exclusions'][0]['reasons']


@pytest.mark.parametrize('invalid', ['-1', 'NaN', 'Infinity'])
def test_invalid_optional_source_value_does_not_discard_valid_features(invalid):
    from decimal import Decimal
    from modules.motor_riesgo.feature_builder import build_observation
    item={key:None for key in ('fecha_adjudicacion','departamento_entidad','buyer_previous','concentration','nit_proveedor_clave',
        'nit_entidad','id_adjudicacion','valor_total_adjudicacion','urlproceso','market_complete','repeated','direct90')}
    item.update(id=1,fuente_id=1,socrata_row_id='ROW1',id_del_proceso='P1',adjudicado='NO',estado_del_procedimiento='Publicado',
        fecha_de_publicacion_del=datetime(2026,10,1,tzinfo=timezone.utc),codigo_principal_de_categoria='X',
        modalidad_de_contratacion='X',precio_base=Decimal('100'),duracion=Decimal(invalid),unidad_de_duracion='dias')
    captured=build_observation(item,'2026-10-16T12:00:00+00:00')
    result=predict(artifact(),captured)
    assert result['index'] is None and 'dato_invalido:duracion_dias' in result['reasons']
    assert 'sin_reconstruccion_temporal_de_etapa' in result['reasons']
    assert result['values']['log_presupuesto'] is not None
    item['precio_base']=Decimal(invalid)
    captured=build_observation(item,'2026-10-16T12:00:00+00:00')
    result=predict(artifact(),captured)
    assert result['index'] is None and result['provenance']['source_row_id']=='ROW1'


def test_duplicate_observation_and_tampered_snapshot_rejected():
    item=observation()
    with pytest.raises(ValueError,match='duplicada'):
        prepare_rows([item,item],{},'CONVOCATORIA')
    rows,coverage=prepare_rows([{**item,'snapshot':{},'snapshot_sha256':'wrong'}],{},'CONVOCATORIA')
    assert rows == [] and coverage['excluded']['snapshot_alterado'] == 1


def test_temporal_minimum_case_groups_and_labels_not_available_at_training():
    with pytest.raises(ValueError,match='15 expedientes'):
        temporal_split([])
    rows=[]
    for i in range(30):
        at=f'{2000+i}-01-01T00:00:00+00:00'
        rows += [{'prediction_at':at,'positive':True,'case_group':str(i),'label_available_at':f'{2000+i}-02-01T00:00:00+00:00'},
                 {'prediction_at':at,'positive':False,'case_group':None}]
    rows[0]['label_available_at']='2099-01-01T00:00:00+00:00'
    rows[36]['label_available_at']='2099-01-01T00:00:00+00:00'
    train,validation,test=temporal_split(rows)
    assert len(train)==36 and len(validation)==12
    assert train[0]['positive'] is False and train[0]['case_group'] is None
    assert validation[0]['positive'] is False and validation[0]['label_available_at'] is None
    assert max(r['prediction_at'] for r in train) < min(r['prediction_at'] for r in validation)
    assert max(r['prediction_at'] for r in validation) < min(r['prediction_at'] for r in test)
    result=paired_case_interval(test,[float(r['positive']) for r in test],[0.]*len(test))
    assert result['passed'] is True
    assert paired_case_interval(test,[0.]*len(test),[0.]*len(test))['passed'] is False


def test_daily_due_at_0300_bogota():
    from modules.motor_riesgo.pipeline import due_day
    assert due_day(datetime(2026,10,16,7,59,tzinfo=timezone.utc))=='2026-10-15'
    assert due_day(datetime(2026,10,16,8,0,tzinfo=timezone.utc))=='2026-10-16'


def test_ml_training_optional_and_api_has_no_sklearn_import():
    from main import app
    assert app
    assert 'sklearn' not in sys.modules


def test_training_roundtrip_in_separate_environment(tmp_path):
    interpreter=os.environ.get('TEST_ML_PYTHON')
    if not interpreter:
        pytest.skip('TEST_ML_PYTHON explícito requerido')
    source=Path(__file__).with_name('risk_training_smoke.py')
    # Match the bounded thread policy of the production process launcher.
    environment={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1',
                 'PYTHONHASHSEED':'0','PYTHONNOUSERSITE':'1'}
    result=subprocess.run([interpreter,str(source),str(tmp_path/'model.json')],env=environment,
                          capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stderr
    model=json.loads((tmp_path/'model.json').read_text())
    validate_artifact(model)
    assert model['algorithm']=='PU-bagging-logistic-mean-margin'


def test_compressed_joint_inference_reads_once_and_preserves_independent_stage_results(tmp_path):
    import hashlib
    from analytics_ml.streams import binary_stream,logical_sha256
    interpreter=os.environ.get('TEST_ML_INFERENCE_PYTHON')
    if not interpreter:
        pytest.skip('TEST_ML_INFERENCE_PYTHON explícito requerido')
    models={stage:artifact(stage) for stage in ('CONVOCATORIA','ADJUDICACION')}
    model_path=tmp_path/'models.json';model_path.write_text(json.dumps(models),encoding='utf-8')
    dataset=tmp_path/'observations.jsonl.gz'
    with binary_stream(dataset,'xb') as output:
        for stage in models:
            output.write((json.dumps(observation(stage),ensure_ascii=False)+'\n').encode('utf-8'))
    entry=Path(__file__).resolve().parents[1]/'scripts/risk_process.py'
    outputs=[]
    for run in range(2):
        output=tmp_path/f'results-{run}.jsonl.gz'
        result=subprocess.run([interpreter,'-I',str(entry),'infer','--models',str(model_path),'--observations',str(dataset),'--output',str(output)],
                              capture_output=True,text=True,timeout=30)
        assert result.returncode==0,result.stderr
        manifest=json.loads(Path(str(output)+'.manifest.json').read_text(encoding='utf-8'))
        assert manifest['input_rows']==2 and manifest['counts']=={'CONVOCATORIA':1,'ADJUDICACION':1}
        assert manifest['observations_sha256']==logical_sha256(dataset)
        assert manifest['output_sha256']==hashlib.sha256(output.read_bytes()).hexdigest()
        with binary_stream(output,'rb') as source:
            records=[json.loads(line) for line in source]
        assert [r['result']['index'] for r in records]==[predict(models[s],observation(s))['index'] for s in models]
        outputs.append(output.read_bytes())
    assert outputs[0]==outputs[1]
    with pytest.raises(ValueError,match='límite'):
        logical_sha256(dataset,1)
