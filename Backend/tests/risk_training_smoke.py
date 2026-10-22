"""Synthetic only. This script cannot register or activate operational models."""
import json
from pathlib import Path
import sys
from math import log1p
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analytics_ml.training import train
from analytics_ml.inference import raw_score,vector
from modules.motor_riesgo.domain import NUMERIC,CATEGORICAL,digest

rows=[]
for year in range(1980,2020):
    at=f'{year}-01-01T00:00:00+00:00'
    for i in range(100):
        positive=i==0
        values={n: float(10 if positive else 1) for n in NUMERIC['CONVOCATORIA']}
        # Nonconstant comparable budgets make IQR evaluable without making it
        # identify the synthetic label. Other features retain the PU signal.
        values['log_presupuesto'] = log1p(100 + i)
        values.update({n:'X' for n in CATEGORICAL})
        rows.append({'prediction_at':at,'positive':positive,'case_group':str(year) if positive else None,
                    'label_available_at':f'{year}-02-01T00:00:00+00:00' if positive else None,
                    'supplier_group':f'{year}-{i}','values':values})
def synthetic_receipt(data):
    from analytics_ml.evidence import POLICY
    # Explicit synthetic proof exercises engineering only; never registered.
    return {'policy':POLICY, 'registry_sha256':digest({'synthetic_only':True}),
            'verified_rows':len(data), 'verified_dataset_sha256':digest(data)}
model,report=train(rows,'CONVOCATORIA','synthetic-test',evidence=synthetic_receipt(rows))
assert {'modules/motor_riesgo/'+name for name in ('annual_context.py','annual_materialize.py',
        'rolling_materialize.py','method_reference.py')} <= report['runtime_manifest']['files_sha256'].keys()
assert 'sqlalchemy' not in sys.modules  # Recording SQL source hashes must not import API dependencies.
again,repeated=train(rows,'CONVOCATORIA','synthetic-test',evidence=synthetic_receipt(rows))
assert again==model and repeated==report
assert report['slices']['periodo']
award_rows=[{**r,'values':{**r['values'],**{n:float(10 if r['positive'] else 1) for n in NUMERIC['ADJUDICACION']}}} for r in rows]
award_model,award_report=train(award_rows,'ADJUDICACION','synthetic-award-test',evidence=synthetic_receipt(award_rows))
# In this fixture, direct/reiteration rules already recover all positives.
# A fitted award model must stay unapproved when it cannot improve on them.
assert not award_report['validated'] and not award_report['case_interval']['passed']
assert award_model['stage']=='ADJUDICACION'
Path(sys.argv[1]).write_text(json.dumps(model),encoding='utf-8')
assert report['case_interval']['passed'] and report['unseen_suppliers']['passed']
assert model['runtime_manifest_sha256']==digest(report['runtime_manifest'])
assert model['split_audit_sha256']==digest(report['split_audit'])
assert report['split_audit']['excluded_rows']==0
assert report['baseline_complete_for_comparison'] is True
assert report['baseline_coverage']['complete_rows'] == report['split_sizes'][2]
assert 'operation_coverage' not in report['baseline_coverage']
assert report['baseline_coverage']['operation_coverage_sha256']
from analytics_ml.approval import validate_approval
validate_approval(model,report,'CONVOCATORIA','synthetic-test',True)
# One validation case begins at the earlier boundary of another case. The
# chronological splitter excludes the displaced case row, without losing its
# accounting or treating it as a positive in another block.
spanning_rows=rows+[{**rows[(2007-1980)*100], 'prediction_at':'2003-01-01T00:00:00+00:00'}]
spanning_model,spanning_report=train(spanning_rows,'CONVOCATORIA','synthetic-spanning',evidence=synthetic_receipt(spanning_rows))
assert spanning_report['split_audit']['excluded_rows']==1
assert sum(spanning_report['split_sizes'])+1==len(spanning_rows)
validate_approval(spanning_model,spanning_report,'CONVOCATORIA','synthetic-spanning',True)
assert report['runtime_manifest']['dependencies']['scikit-learn']
assert 'analytics_ml/requirements-training.lock' in report['runtime_manifest']['files_sha256']
assert not {'modules/motor_riesgo/service.py','modules/motor_riesgo/process_runner.py','modules/motor_riesgo/windows_job.py'} & set(report['runtime_manifest']['files_sha256'])
assert raw_score(model,rows[0]['values'])[0]>raw_score(model,rows[1]['values'])[0]
print(json.dumps({'synthetic_only':True,'passed':True,'rows':len(rows)}))
