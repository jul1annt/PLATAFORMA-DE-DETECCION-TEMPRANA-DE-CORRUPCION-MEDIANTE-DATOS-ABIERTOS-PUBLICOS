"""Public methodology must describe implemented boundaries without implying calibration."""
from modules.motor_riesgo.catalog import INDICATORS, development_reference
from modules.motor_riesgo.controller import methodology
from modules.motor_riesgo.baseline_coverage import baseline_coverage


def test_public_reference_uses_actual_family_weights_and_stage_applicability():
    data=methodology();reference=data['development_reference']
    actual=baseline_coverage({},'ADJUDICACION')
    assert reference['family_weights']=={name:value['weight'] for name,value in actual['families'].items()}
    assert reference['families_by_stage']['CONVOCATORIA']==['IMPORTE_ATIPICO']
    assert len(reference['families_by_stage']['ADJUDICACION'])==3
    assert not reference['weights_calibrated'] and not reference['reference_index_0_100']
    assert not reference['missing_data_is_zero'] and not reference['corruption_probability']
    assert not reference['automatic_response_counter_to_bidder_mapping']
    assert not reference['historical_training_from_current_cut_allowed']
    assert not reference['annual_context_is_extra_family_point']
    assert reference['policy_version'] == 'base-analitica-pesos-v8'
    assert reference['priority_analysis']['weight_range'] == {'minimum':'0.80','maximum':'1.20'}
    assert not reference['priority_analysis']['ranking_is_total_order']
    assert reference['legacy_provider_score_is_separate']
    assert data['index_scope'] and data['publication_gate']


def test_reference_metadata_is_not_a_mutable_global_configuration():
    reference=development_reference();reference['family_weights']['IMPORTE_ATIPICO']=999
    reference['family_indicators']['IMPORTE_ATIPICO'].append('FAKE')
    fresh=development_reference()
    assert fresh['family_weights']['IMPORTE_ATIPICO']==1
    assert fresh['family_indicators']['IMPORTE_ATIPICO']==['IMPORTE_ATIPICO']


def test_catalog_keeps_unknown_denominator_and_actual_bidder_limits_explicit():
    indicators={row['id']:row for row in INDICATORS}
    annual=indicators['CONCENTRACION_PREVIA'];bidder=indicators['OFERENTE_UNICO']
    assert 'denominador completo' in ' '.join(annual['requires'])
    assert 'excluyendo todo el proceso objetivo' in annual['formula']
    assert 'no cuota monetaria ni HHI' in annual['limits']
    assert 'subconjunto conocido' in annual['limits']
    assert 'no acreditan oferentes reales' in bidder['limits']
    assert 'lote' in ' '.join(bidder['requires'])


def test_public_http_methodology_requires_no_training_or_database_session():
    from fastapi.testclient import TestClient
    from main import app
    client=TestClient(app)
    try:
        response=client.get('/api/riesgo/metodologia')
        assert response.status_code==200
        data=response.json()
        assert data['development_reference']['family_weights']['IMPORTE_ATIPICO']==1
        assert not data['development_reference']['weights_calibrated']
    finally:client.close()
