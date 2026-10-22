"""Monetary semantics use synthetic fixtures, never judicial training labels."""
from copy import deepcopy
import math
import pytest
from analytics_ml.evidence import validate_record, verified_observations, POLICY
from modules.motor_riesgo.domain import digest
from test_risk_engine import observation
from test_risk_feature_evidence import reviewed_record, entry


@pytest.mark.parametrize('stage', ['CONVOCATORIA', 'ADJUDICACION'])
def test_explicit_nominal_cop_amounts_retain_the_reviewed_log_values(tmp_path, stage):
    record = reviewed_record(tmp_path, observation(stage))
    validate_record(record, tmp_path)
    item = {**record['observation'], 'feature_evidence_id': record['evidence_id']}
    rows, report = verified_observations([item], [entry(record)], tmp_path)
    assert rows == [item] and report['policy'] == POLICY
    assert report['policy'] == 'reviewed-physical-stage-evidence-v2'


@pytest.mark.parametrize('stage', ['CONVOCATORIA', 'ADJUDICACION'])
@pytest.mark.parametrize('tamper', ['missing', 'unreviewed', 'currency', 'constant', 'vpit',
    'millions', 'measure', 'transform', 'hash', 'locator', 'log', 'zero', 'negative',
    'nan', 'infinite', 'invalid_decimal', 'numeric_raw', 'overflow', 'boolean_log'])
def test_unsupported_or_unreviewed_money_cannot_enter_either_stage(tmp_path, stage, tamper):
    record = reviewed_record(tmp_path, observation(stage))
    name = 'log_adjudicado' if stage == 'ADJUDICACION' else 'log_presupuesto'
    field = record['observation']['fields'][name]
    assertion = record['field_evidence'][name]
    money = field['monetary']
    if tamper == 'missing': del field['monetary']
    elif tamper == 'unreviewed': record['review']['monetary_basis_verified'] = False
    elif tamper == 'currency': money['currency'] = 'USD'
    elif tamper == 'constant': money['price_basis'] = 'CONSTANT_2008'
    elif tamper == 'vpit': money['measure'] = 'VPIT'
    elif tamper == 'millions': money['unit'] = 'MILLONES_DE_PESOS'
    elif tamper == 'measure': money['measure'] = 'VALOR_ADJUDICADO' if stage == 'CONVOCATORIA' else 'PRESUPUESTO_PROCESO'
    elif tamper == 'transform': money['transform'] = 'LOG10'
    elif tamper == 'hash': assertion['monetary_sha256'] = '0' * 64
    elif tamper == 'locator': assertion['monetary_locator'] = ' '
    elif tamper == 'log': field['value'] = 99.
    elif tamper == 'zero': money['raw_amount'] = '0'
    elif tamper == 'negative': money['raw_amount'] = '-1'
    elif tamper == 'nan': money['raw_amount'] = 'NaN'
    elif tamper == 'infinite': money['raw_amount'] = 'Infinity'
    elif tamper == 'invalid_decimal': money['raw_amount'] = '$ 1.234,56'
    elif tamper == 'numeric_raw': money['raw_amount'] = math.expm1(field['value'])
    elif tamper == 'overflow': money['raw_amount'] = '1e99999'
    elif tamper == 'boolean_log': field['value'] = True
    # A matching integrity hash does not make an unsupported quantity valid.
    if tamper != 'hash' and tamper != 'missing':
        assertion['monetary_sha256'] = digest(money)
    assertion['value_sha256'] = digest(field['value'])
    with pytest.raises(ValueError):
        validate_record(record, tmp_path)
    item = {**record['observation'], 'feature_evidence_id': record['evidence_id']}
    rows, report = verified_observations([item], [entry(record)], tmp_path)
    assert not rows and report['excluded'] == {'evidencia_fisica_no_verificada': 1}


def test_missing_money_does_not_discard_separately_evidenced_nonmonetary_fields(tmp_path):
    record = reviewed_record(tmp_path)
    del record['observation']['fields']['log_presupuesto']
    del record['field_evidence']['log_presupuesto']
    del record['review']['monetary_basis_verified']
    validate_record(record, tmp_path)
    item = {**record['observation'], 'feature_evidence_id': record['evidence_id']}
    rows, report = verified_observations([item], [entry(record)], tmp_path)
    assert rows == [item] and report['verified_rows'] == 1
    from analytics_ml.corpus import prepare_rows
    usable, coverage = prepare_rows(rows, {}, 'CONVOCATORIA')
    assert not usable and coverage['excluded'] == {'variables_esenciales_ausentes': 1}


def test_monetary_metadata_cannot_be_changed_under_the_previous_review_hash(tmp_path):
    record = reviewed_record(tmp_path)
    registered = entry(deepcopy(record))
    record['observation']['fields']['log_presupuesto']['monetary']['currency'] = 'USD'
    item = {**record['observation'], 'feature_evidence_id': record['evidence_id']}
    assert verified_observations([item], [registered], tmp_path)[1]['excluded'] == {'observacion_distinta_de_revision': 1}


def test_tiny_positive_amount_cannot_masquerade_as_zero_after_the_transform(tmp_path):
    record = reviewed_record(tmp_path)
    field = record['observation']['fields']['log_presupuesto']
    field['monetary']['raw_amount'] = '0.00000000001'
    field['value'] = 0.
    record['field_evidence']['log_presupuesto'].update(
        value_sha256=digest(0.), monetary_sha256=digest(field['monetary']))
    with pytest.raises(ValueError):
        validate_record(record, tmp_path)
