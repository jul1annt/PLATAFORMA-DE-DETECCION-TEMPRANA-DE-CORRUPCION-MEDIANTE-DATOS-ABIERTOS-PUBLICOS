"""Registered responses cannot silently become bidders, even with valid counts."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest
from modules.motor_riesgo.competition_context import assess, observe, metric, FIELDS


def row(**changes):
    return {'contract_id': 1, 'source_id': 1, 'source_row_id': 'ROW', 'process_id': 'PROC', 'award_id': 'AWARD',
            'awarded': 'SI', 'method': 'LICITACION PUBLICA', 'global_unit_rows_up_to_two': 1,
            'proveedores_unicos_con': '1', 'numero_de_lotes': '1', 'selection_groups': ['sample'], **changes}


def payload(rows=None):
    rows = rows or [row()]
    return {'scope': {'rows': len(rows), 'source_datasets': {'1': 'p6dx-8zbt'},
                      'temporal_scope': 'current_cut_descriptive_not_stage_prediction'}, 'rows': rows}


@pytest.mark.parametrize('value,state', [(None,'AUSENTE'), ('0','CERO'), ('1.0','UNO'), (2,'MULTIPLE'),
    (True,'INVALIDO'), ('-1','INVALIDO'), ('1.5','INVALIDO'), ('NaN','INVALIDO'), ('Infinity','INVALIDO'),
    ('1e99999999','INVALIDO'), ('2147483648','INVALIDO')])
def test_counter_quality_preserves_zero_missing_and_invalid(value, state):
    assert metric(value)['state'] == state


@pytest.mark.parametrize('changes', [{}, {'numero_de_lotes': 2}, {'numero_de_lotes': 0},
    {'respuestas_al_procedimiento': 1}, {'conteo_de_respuestas_a_ofertas': 1},
    {'proveedores_invitados': 999}, {'proveedores_que_manifestaron': 999}])
def test_responses_never_enable_actual_bidders_or_weighted_feature(changes):
    result = observe(row(**changes), 'p6dx-8zbt')
    assert result['response_pattern'] == 'UN_PROVEEDOR_CON_RESPUESTA_DECLARADO'
    assert result['actual_bidders'] is None and result['model_values'] == {}
    assert not result['scoring_eligible'] and not result['training_eligible'] and not result['publication_authorized']


def test_missing_unique_counter_has_no_fallback_to_other_counts():
    result = observe(row(proveedores_unicos_con=None, respuestas_al_procedimiento=1,
                          conteo_de_respuestas_a_ofertas=1, proveedores_invitados=1), 'p6dx-8zbt')
    assert result['response_pattern'] == 'NO_EVALUABLE' and result['actual_bidders'] is None


def test_unrecognized_source_does_not_inherit_semantics():
    result = observe(row(), 'another-dataset')
    assert not result['source_schema_recognized'] and result['response_pattern'] == 'NO_EVALUABLE'


def test_distinct_process_summary_and_conflicting_award_rows():
    rows = [row(), row(contract_id=2, award_id='AWARD2', source_row_id='ROW2'),
            row(contract_id=3, process_id='OTHER', award_id='AWARD3', proveedores_unicos_con='2')]
    data = payload(rows); before = copy.deepcopy(data); result = assess(data)
    assert before == data and result == assess(data)
    summary = result['summary']['sample']
    assert summary['selected_rows'] == 3 and summary['observed_processes'] == 2
    assert summary['process_unique_counter_states'] == {'UNO': 1, 'MULTIPLE': 1}
    rows[1]['proveedores_unicos_con'] = None
    summary = assess(payload(rows))['summary']['sample']
    assert summary['process_unique_counter_states']['DISCREPANTE_O_INCOMPLETO_ENTRE_FILAS_OBSERVADAS'] == 1
    assert summary['process_consistency_scope'] == 'selected_rows_only_not_complete_process_frame'


def test_ambiguous_operation_stays_visible_but_not_admissible():
    result = observe(row(global_unit_rows_up_to_two=2), 'p6dx-8zbt')
    assert not result['operation_identity_admissible'] and not result['scoring_eligible']


@pytest.mark.parametrize('change', [{'rows': 2}, {'temporal_scope': 'historical_stage'}])
def test_invalid_scope_rejected(change):
    data = payload(); data['scope'].update(change)
    with pytest.raises(ValueError): assess(data)


def test_duplicate_rows_and_selection_labels_rejected():
    with pytest.raises(ValueError): assess(payload([row(), row()]))
    with pytest.raises(ValueError): assess(payload([row(selection_groups=['sample','sample'])]))


@pytest.mark.parametrize('awarded', ['SI','NO'])
def test_capture_does_not_map_populated_response_counters_to_bidders(awarded):
    from datetime import datetime, timezone
    from modules.motor_riesgo.feature_builder import build_observation
    item={key:None for key in ('buyer_previous','concentration','nit_proveedor_clave','nit_entidad',
        'departamento_entidad','duracion','unidad_de_duracion','urlproceso')}
    item.update(id=1,fuente_id=1,socrata_row_id='ROW',id_del_proceso='P',id_adjudicacion='A',
                adjudicado=awarded,estado_del_procedimiento='Seleccionado' if awarded=='SI' else 'Publicado',
                fecha_de_publicacion_del=datetime(2026,1,1,tzinfo=timezone.utc),
                fecha_adjudicacion=datetime(2026,1,2,tzinfo=timezone.utc) if awarded=='SI' else None,
                codigo_principal_de_categoria='80161500',modalidad_de_contratacion='LICITACION PUBLICA',
                precio_base=100,valor_total_adjudicacion=100,oferentes=1,**{field:1 for field in FIELDS})
    observed=build_observation(item,'2026-10-20T12:00:00Z')
    assert observed is not None and 'oferentes' not in observed['fields']


def test_cli_checks_frozen_evidence_and_does_not_overwrite(tmp_path):
    source = tmp_path/'input.json'; source.write_text(json.dumps(payload()))
    entries=[]
    files={'dictionary_2022.pdf':b'%PDF-synthetic', 'dictionary_public.pdf':b'%PDF-synthetic2',
           'dataset_metadata.json':json.dumps({'id':'p6dx-8zbt','columns':[{'fieldName':field,'dataTypeName':'number','description':'synthetic'} for field in FIELDS]}).encode()}
    for name, body in files.items():
        (tmp_path/name).write_bytes(body)
        entries.append({'file':name,'status':200,'sha256':hashlib.sha256(body).hexdigest(),'url':'https://www.datos.gov.co/synthetic/'+name})
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(entries));output=tmp_path/'report.json'
    script=Path(__file__).resolve().parents[1]/'scripts/risk_competition_audit.py'
    command=[sys.executable,'-I','-S',str(script),'--input',str(source),'--source-manifest',str(manifest),'--output',str(output)]
    result=subprocess.run(command,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    report=json.loads(output.read_text(encoding='utf-8'))
    assert len(report['reviewed_sources'])==3 and len(report['implementation_sha256'])==7
    assert not report['actual_bidder_field_verified'] and not report['actual_bidder_fallback_enabled']
    before=output.read_bytes()
    assert subprocess.run(command,capture_output=True).returncode!=0 and output.read_bytes()==before
    (tmp_path/'dictionary_public.pdf').write_bytes(b'changed')
    command[-1]=str(tmp_path/'another-report.json')
    assert subprocess.run(command,capture_output=True).returncode!=0
    assert not (tmp_path/'another-report.json').exists()
