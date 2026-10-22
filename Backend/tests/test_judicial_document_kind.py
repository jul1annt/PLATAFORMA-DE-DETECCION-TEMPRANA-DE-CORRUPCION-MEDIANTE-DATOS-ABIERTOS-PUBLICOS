"""A final procedural order cannot replace a final conviction."""
from copy import deepcopy
import hashlib
import pytest
from analytics_ml.corpus import verified_cases


def synthetic_case(root):
    # Explicit engineering fixtures, not real decisions or training labels.
    judgment=b'SYNTHETIC CONVICTION FIXTURE';finality=b'SYNTHETIC FINALITY FIXTURE'
    (root/'judgment.txt').write_bytes(judgment);(root/'finality.txt').write_bytes(finality)
    checksum=hashlib.sha256(judgment).hexdigest()
    return {'case_id':'fixture','authority':'Synthetic test only','docket':'TEST-NOT-A-REAL-DOCKET',
        'conduct':'CORRUPCION','status':'VERIFICADO','published_at':'2023-02-01T00:00:00Z','final_at':'2023-01-01T00:00:00Z',
        'first_investigation_at':'2021-01-01T00:00:00Z','verified_by':'synthetic-reviewer',
        'judgment':{'file':'judgment.txt','url':'https://www.ramajudicial.gov.co/synthetic-fixture',
                    'sha256':checksum,'kind':'SENTENCIA_CONDENATORIA'},
        'finality':{'file':'finality.txt','url':'https://www.ramajudicial.gov.co/synthetic-fixture-finality',
                    'sha256':hashlib.sha256(finality).hexdigest(),'kind':'CONSTANCIA_EJECUTORIA','judgment_sha256':checksum,
                    'reviewed':True,'effect':'FIRMEZA_CONFIRMADA','locator':'Synthetic finality, paragraph 1'},
        'operations':[{'source_id':1,'source_row_id':'FICTITIOUS','process_id':'FICTITIOUS','match':'EXACTO',
                       'judicial_link':{'judgment_sha256':checksum,'outcome':'CONDENA_CORRUPCION','reviewed':True,
                                        'facts_locator':'Synthetic facts, paragraph 1','operative_locator':'Synthetic disposition, item 1'}}]}


@pytest.mark.parametrize('kind',['AUTO_RECONOCIMIENTO_VICTIMAS','TUTELA','AUTO_ARCHIVO','ANUNCIO_SENTIDO_FALLO',None])
def test_final_procedural_decisions_are_never_positive_convictions(tmp_path,kind):
    record=synthetic_case(tmp_path);record['judgment']['kind']=kind
    accepted,report=verified_cases([record],tmp_path)
    assert accepted=={} and report['eligible_cases']==0
    assert 'falta_sentencia_condenatoria_identificada' in report['exclusions'][0]['reasons']


@pytest.mark.parametrize('tamper',['kind','link'])
def test_finality_must_identify_the_specific_conviction(tmp_path,tamper):
    record=synthetic_case(tmp_path)
    if tamper=='kind':record['finality']['kind']='AUTO_RECONOCIMIENTO_VICTIMAS'
    else:record['finality']['judgment_sha256']='f'*64
    assert verified_cases([record],tmp_path)[0]=={}
    assert verified_cases([synthetic_case(tmp_path)],tmp_path)[0]


@pytest.mark.parametrize('effect',['APERTURA_TERMINO','VENCIMIENTO_PREVISTO','RECURSO_PENDIENTE',
                                  'AUTO_PROCESAL_EJECUTORIADO',None])
def test_title_and_elapsed_period_do_not_establish_final_conviction(tmp_path,effect):
    record=synthetic_case(tmp_path)
    record['finality']['effect']=effect
    # Keep physical files, hashes, dates and the tempting document title valid.
    accepted,report=verified_cases([record],tmp_path)
    assert not accepted
    assert 'firmeza_sin_efecto_confirmado_y_revisado' in report['exclusions'][0]['reasons']


@pytest.mark.parametrize('change',['unreviewed','missing_review','blank_locator','missing_locator'])
def test_finality_requires_review_and_a_locator_of_its_actual_effect(tmp_path,change):
    record=synthetic_case(tmp_path)
    if change=='unreviewed':record['finality']['reviewed']=False
    elif change=='missing_review':record['finality'].pop('reviewed')
    elif change=='blank_locator':record['finality']['locator']=' '
    else:record['finality'].pop('locator')
    assert not verified_cases([record],tmp_path)[0]


@pytest.mark.parametrize('tamper',['NULIDAD','ABSOLUCION','INVESTIGACION','FRAUDE_CONTRACTUAL',
                                  'no_locator','wrong_hash','missing','unreviewed'])
def test_each_operation_requires_review_of_convicted_facts_and_disposition(tmp_path,tamper):
    record=synthetic_case(tmp_path);operation=record['operations'][0];link=operation['judicial_link']
    if tamper=='no_locator':link['operative_locator']=' '
    elif tamper=='wrong_hash':link['judgment_sha256']='f'*64
    elif tamper=='missing':operation.pop('judicial_link')
    elif tamper=='unreviewed':link['reviewed']=False
    else:link['outcome']=tamper
    accepted,inventory=verified_cases([record],tmp_path)
    assert not accepted
    assert 'operacion_sin_condena_por_corrupcion_documentada' in inventory['exclusions'][0]['reasons']


def test_mixed_dispositions_never_turn_every_operation_into_a_positive(tmp_path):
    record=synthetic_case(tmp_path)
    disputed=deepcopy(record['operations'][0]);disputed['source_row_id']='OTHER-ROW';disputed['process_id']='OTHER-PROCESS'
    disputed['judicial_link']['outcome']='NULIDAD';record['operations'].append(disputed)
    assert not verified_cases([record],tmp_path)[0]
    # The human-reviewed registry must retain only the expressly convicted
    # operation in its positive links; other facts remain research context.
    record['operations'].pop()
    assert verified_cases([record],tmp_path)[0]


def subsequent_finality_case(root):
    record=synthetic_case(root)
    record['finality'].update(kind='PROVIDENCIA_ACREDITA_FIRMEZA',
        declared_final_at=record['final_at'],
        declaration_date_locator='Synthetic subsequent decision, antecedents paragraph 2')
    return record


def test_subsequent_decision_requires_explicit_dated_finality(tmp_path):
    record=subsequent_finality_case(tmp_path)
    accepted,report=verified_cases([record],tmp_path)
    assert accepted and report['judicial_review_policy']=='reviewed-finality-effect-v2'
    # Equivalent instants with an explicit timezone are valid.
    record['finality']['declared_final_at']='2022-12-31T19:00:00-05:00'
    assert verified_cases([record],tmp_path)[0]


@pytest.mark.parametrize('date',[None,'','2023-01-01','not-a-date',{},[],False])
def test_subsequent_decision_without_documented_finality_date_is_excluded(tmp_path,date):
    record=subsequent_finality_case(tmp_path);record['finality']['declared_final_at']=date
    accepted,report=verified_cases([record],tmp_path)
    assert not accepted
    assert 'fecha_firmeza_declarada_ausente_o_invalida' in report['exclusions'][0]['reasons']


@pytest.mark.parametrize('change',['missing_date','different_date','missing_locator','blank_locator',
                                 'unreviewed','procedural_effect','wrong_conviction','missing_original','changed_original'])
def test_subsequent_decision_does_not_bypass_other_finality_requirements(tmp_path,change):
    record=subsequent_finality_case(tmp_path);finality=record['finality']
    if change=='missing_date':finality.pop('declared_final_at')
    elif change=='different_date':finality['declared_final_at']='2024-02-05T00:00:00Z'
    elif change=='missing_locator':finality.pop('declaration_date_locator')
    elif change=='blank_locator':finality['declaration_date_locator']=' '
    elif change=='unreviewed':finality['reviewed']=False
    elif change=='procedural_effect':finality['effect']='AUTO_PROCESAL_EJECUTORIADO'
    elif change=='wrong_conviction':finality['judgment_sha256']='f'*64
    elif change=='missing_original':(tmp_path/'finality.txt').unlink()
    else:(tmp_path/'finality.txt').write_bytes(b'SYNTHETIC ALTERED DOCUMENT')
    assert not verified_cases([record],tmp_path)[0]


def test_subsequent_decision_cannot_make_label_available_before_finality(tmp_path):
    record=subsequent_finality_case(tmp_path)
    record['published_at']='2022-12-31T00:00:00Z'
    assert not verified_cases([record],tmp_path)[0]
