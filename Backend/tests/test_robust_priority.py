import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from decimal import getcontext
from itertools import product
import random

import pytest

from modules.motor_riesgo.baseline_coverage import (
    baseline_coverage, summarize, finding, DETECTED, CLEAR, UNKNOWN, NOT_APPLICABLE,
)
from modules.motor_riesgo.robust_priority import assess, methodology


def row(key, states, stage='ADJUDICACION'):
    names = ('IMPORTE_ATIPICO','OFERENTE_UNICO','DIRECTAS_90D','REITERACION_30D')
    indicators = {name:finding(name,status) for name,status in zip(names,states)}
    return {'contract_id':key,'snapshot_cut':'2026-10-01',
            'coverage':summarize(stage,indicators),'training_eligible':False,'publication_authorized':False}


def report(rows):
    return {'policy':'current-cut-joint-families-v1',
            'temporal_scope':'current_cut_descriptive_not_stage_prediction',
            'snapshot_cut':'2026-10-01','cohort_canonical_sha256':'a'*64,
            'training_eligible':False,'publication_authorized':False,
            'database_generation_consistency_verified':False,'targets':len(rows),'results':rows}


def test_complete_order_and_ties_without_identifier_tie_break():
    data=report([row(1,[DETECTED]*4),row(2,[CLEAR]*4),row(3,[CLEAR]*4)])
    result=assess(data)['results']
    assert [(r['best_rank_bound'],r['worst_rank_bound']) for r in result] == [(1,1),(2,3),(2,3)]
    assert result[0]['strictly_lower_priority_guaranteed']==2
    assert result[1]['review_route']=='SIN_SENAL_OBSERVADA'


def test_missingness_keeps_full_uncertainty_and_routes_confirmed_signals():
    data=report([row(1,[UNKNOWN]*4),row(2,[DETECTED,UNKNOWN,UNKNOWN,UNKNOWN])])
    result=assess(data)
    assert all((r['best_rank_bound'],r['worst_rank_bound'])==(1,2) for r in result['results'])
    assert result['results'][0]['central_weighted_count_interval']=={'min':0,'max':3}
    assert result['results'][1]['central_weighted_count_interval']=={'min':1,'max':3}
    assert result['review_route_counts']=={'COMPLETAR_EVIDENCIA':1,'REVISAR_SENALES_CONFIRMADAS':1}
    assert result['fully_resolved_priorities']==0 and result['model_index'] is None


def test_applicability_and_stage_never_share_a_ranking():
    data=report([row(1,[CLEAR]*4),row(2,[CLEAR,NOT_APPLICABLE,CLEAR,CLEAR]),
                 row(3,[CLEAR,NOT_APPLICABLE,NOT_APPLICABLE,NOT_APPLICABLE],'CONVOCATORIA')])
    result=assess(data)
    assert len(result['groups'])==3
    assert all(r['comparison_population']==1 for r in result['results'])
    assert len({r['comparison_group'] for r in result['results']})==3


def test_or_family_does_not_double_count_or_hide_indicator_missingness():
    result=assess(report([row(1,[CLEAR,CLEAR,DETECTED,UNKNOWN])]))['results'][0]
    assert result['complete_count']==1
    assert result['confirmed_families']==['CONCENTRACION_REITERACION']
    assert result['incomplete_indicator_evidence']
    second=assess(report([row(1,[CLEAR,CLEAR,DETECTED,DETECTED])]))['results'][0]
    assert second['complete_count']==1 and not second['incomplete_indicator_evidence']


def test_equal_counts_different_families_remain_tied_under_weight_uncertainty():
    result=assess(report([row(1,[DETECTED,CLEAR,CLEAR,CLEAR]),row(2,[CLEAR,DETECTED,CLEAR,CLEAR])]))
    assert all((r['best_rank_bound'],r['worst_rank_bound'])==(1,2) for r in result['results'])


def test_bounds_contain_all_sampled_interior_weights_and_missing_completions():
    rng=random.Random(20261020)
    for _ in range(30):
        rows=[row(i+1,[rng.choice([CLEAR,DETECTED,UNKNOWN]) for _ in range(4)]) for i in range(12)]
        output=assess(report(rows))['results']
        for _ in range(20):
            weights=[rng.randint(80,120) for _ in range(3)]
            values=[]
            for item in rows:
                pattern=[v['status'] for v in item['coverage']['families'].values()]
                values.append(sum(w*(1 if s==DETECTED else rng.randint(0,1) if s==UNKNOWN else 0)
                                  for w,s in zip(weights,pattern)))
            for i,result in enumerate(output):
                tied_best=1+sum(v>values[i] for v in values)
                tied_worst=sum(v>=values[i] for v in values)
                assert result['best_rank_bound'] <= tied_best <= tied_worst <= result['worst_rank_bound']


def test_stable_under_reordering_decimal_context_and_does_not_mutate():
    data=report([row(2,[UNKNOWN]*4),row(1,[DETECTED]*4)])
    before=copy.deepcopy(data); result=assess(data)
    old=getcontext().prec
    try:
        getcontext().prec=3
        assert assess(data)==result
    finally:getcontext().prec=old
    assert data==before
    data['results'].reverse()
    reordered=assess(data)
    assert sorted(result['results'],key=lambda r:r['contract_id'])==sorted(reordered['results'],key=lambda r:r['contract_id'])


@pytest.mark.parametrize('mutation',[
    lambda d:d.update(policy='legacy'),
    lambda d:d.update(training_eligible=True),
    lambda d:d.update(publication_authorized=True),
    lambda d:d.update(targets=2),
    lambda d:d.update(snapshot_cut=None),
    lambda d:d.update(snapshot_cut='2026-02-30'),
    lambda d:d.update(cohort_canonical_sha256='x'*64),
    lambda d:d['results'][0].update(contract_id=True),
    lambda d:d['results'][0].update(snapshot_cut='2026-10-02'),
    lambda d:d['results'][0]['coverage'].update(complete_score=999),
    lambda d:d['results'][0]['coverage']['families']['IMPORTE_ATIPICO'].update(weight=2),
    lambda d:d['results'][0]['coverage']['indicators']['IMPORTE_ATIPICO'].update(detected=1),
    lambda d:d['results'][0]['coverage'].update(evaluated_indicators=999),
])
def test_invalid_scope_or_tampered_evidence_is_rejected(mutation):
    data=report([row(1,[CLEAR]*4)])
    mutation(data)
    with pytest.raises(ValueError):assess(data)


def test_duplicate_ids_empty_rows_and_cross_stage_indicators_are_rejected():
    data=report([row(1,[CLEAR]*4),row(1,[CLEAR]*4)])
    with pytest.raises(ValueError):assess(data)
    with pytest.raises(ValueError):assess(report([]))
    with pytest.raises(ValueError):assess(report([row(1,[CLEAR]*4,'CONVOCATORIA')]))


def test_stated_generation_is_not_a_new_verification_and_policy_is_not_mutable():
    data=report([row(1,[CLEAR]*4)]);data['database_generation_consistency_verified']=True
    result=assess(data)
    assert not result['database_generation_consistency_verified']
    assert result['input_declares_generation_consistency']
    policy=methodology();policy['central_family_weights']['COMPETENCIA']=999
    assert methodology()['central_family_weights']['COMPETENCIA']==1


def test_cli_is_standalone_reproducible_preserves_files_and_rejects_duplicate_json(tmp_path):
    source=tmp_path/'input.json';output=tmp_path/'output.json'
    source.write_text(json.dumps(report([row(1,[UNKNOWN]*4)])),encoding='utf-8')
    script=Path(__file__).resolve().parents[1]/'scripts/risk_robust_priority.py'
    command=[sys.executable,'-I','-S',str(script),'--input',str(source),'--output',str(output)]
    completed=subprocess.run(command,capture_output=True,text=True)
    assert completed.returncode==0,completed.stderr
    result=json.loads(output.read_text(encoding='utf-8'))
    assert result['input_file_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
    assert len(result['implementation_sha256'])==4
    before=output.read_bytes()
    assert subprocess.run(command,capture_output=True).returncode!=0 and output.read_bytes()==before
    command[-1]=str(tmp_path/'replay.json')
    assert subprocess.run(command,capture_output=True).returncode==0
    assert Path(command[-1]).read_bytes()==before
    source.write_text('{"policy":"x","policy":"y"}',encoding='utf-8')
    command[-1]=str(tmp_path/'invalid.json')
    assert subprocess.run(command,capture_output=True).returncode!=0
    assert not Path(command[-1]).exists()
