"""Independent reference parity through yearly materialization and capture."""
from datetime import datetime, timezone
import pytest
from sqlalchemy import text
from test_risk_engine_postgres import source,row
from modules.motor_riesgo.annual_context import assess, POLICY
from modules.motor_riesgo.history import prepare_context
from modules.motor_riesgo.feature_store import fetch_batch
from modules.motor_riesgo.feature_builder import build_observation

AT='2020-04-01T05:00:00+00:00'


def setup(db,scenario):
    src=source(db);records=[]
    def add(process,supplier='900000001',*,src_item=None,pub='2020-03-01T05:00:00+00:00',
            award_at='2020-03-20T05:00:00+00:00',award=None,status='SI',raw_buyer=None,normalized_buyer=True):
        index=len(records)+1;r,c=row(db,src_item or src,index,datetime(2020,3,1).date(),process=process,provider=supplier)
        r.adjudicado=status;r.estado_del_procedimiento='Seleccionado' if status=='SI' else 'Publicado'
        r.fecha_de_publicacion_del=datetime.fromisoformat(pub) if pub else None
        r.fecha_adjudicacion=datetime.fromisoformat(award_at) if award_at else None
        r.id_adjudicacion=award or 'A-'+str(index);r.nit_entidad=raw_buyer
        c.nit_entidad=str(src.id) if normalized_buyer else None
        records.append((r,c));return r,c
    current,_=add('TARGET',award_at=AT)
    if scenario=='empty':pass
    elif scenario=='usual':
        add('P1');add('P2');add('P3','900000002')
    elif scenario=='tied_leader_outside_target':
        add('P1');add('P2','900000002');add('P3','900000002')
    elif scenario=='all_leaders_win_target':
        add('TARGET','900000002');add('P1');add('P2','900000002')
    elif scenario=='multiple_awards':
        add('P');add('P');add('P','900000002')
    elif scenario=='unknown_date_old_publication':add('BAD',pub='2010-01-01T00:00:00Z',award_at=None)
    elif scenario=='missing_provider':add('BAD',supplier=None)
    elif scenario=='missing_normalization':add('BAD',raw_buyer=str(src.id),normalized_buyer=False)
    elif scenario=='conflicting_buyer':
        _,c=add('BAD',raw_buyer=str(src.id));c.nit_entidad=str(src.id)+'0'
    elif scenario=='unprocessed_raw':
        _,c=add('BAD',raw_buyer=str(src.id));db.delete(c)
    elif scenario=='own_bad_date':add('TARGET',pub=None,award_at=None)
    elif scenario=='missing_publication':add('P',pub=None)
    elif scenario=='alias':add('P',award='A');add(' P ',award='A')
    elif scenario=='other_source':add('P');add('P','900000002',src_item=source(db))
    elif scenario=='boundaries':
        add('START',pub='2019-04-02T05:00:00+00:00',award_at='2019-04-02T05:00:00+00:00')
        add('OLD',pub='2019-04-02T04:59:59+00:00',award_at='2019-04-02T04:59:59+00:00')
        add('FUTURE',award_at='2020-04-01T05:00:01+00:00')
    else:raise AssertionError(scenario)
    db.flush();return current,records


@pytest.mark.parametrize('scenario',['empty','usual','tied_leader_outside_target','all_leaders_win_target',
    'multiple_awards','unknown_date_old_publication','missing_provider','missing_normalization',
    'own_bad_date','missing_publication','alias','other_source','boundaries','conflicting_buyer','unprocessed_raw'])
def test_annual_sql_matches_reference(postgres_test_session,scenario):
    db=postgres_test_session;current,records=setup(db,scenario)
    sources=sorted({r.fuente_id for r,_ in records});prepare_context(db,sources,AT)
    captured=fetch_batch(db,sources,0);by_id={r['id']:r for r in captured}
    neutral=[{'source_id':r['fuente_id'],'source_row_id':r['socrata_row_id'],'process_id':r['id_del_proceso'],
              'award_id':r['id_adjudicacion'],'buyer_key':r['nit_entidad'],'raw_buyer_key':r['raw_buyer_key'],
              'supplier_key':r['nit_proveedor_clave'],'published_at':r['fecha_de_publicacion_del'].isoformat() if r['fecha_de_publicacion_del'] else None,
              'awarded_at':r['fecha_adjudicacion'].isoformat() if r['fecha_adjudicacion'] else None,
              'awarded':r['adjudicado'],'unit_rows':r['unit_rows']} for r in captured]
    target=next(r for r in neutral if r['process_id']=='TARGET' and r['award_id']==current.id_adjudicacion)
    expected=assess(neutral,target,AT);actual=by_id[current.id]
    assert actual['buyer_previous']==expected['buyer_previous']
    assert actual['market_processes']==expected['market_processes']
    assert actual['annual_bad_market']==expected['market_bad_rows']
    assert actual['annual_bad_pub']==expected['publication_bad_rows']
    assert actual['annual_maximum']==expected['max_supplier_processes']
    assert actual['market_complete']==expected['market_complete']
    if expected['concentration'] is None:assert actual['concentration'] is None
    else:assert float(actual['concentration'])==pytest.approx(expected['concentration'])
    observed=build_observation(actual,AT)
    assert observed['fields'].get('procesos_previos',{}).get('value')==expected['buyer_previous']
    assert observed['fields'].get('concentracion_previa',{}).get('value')==expected['concentration']
    assert observed['context']['concentracion_previa']['policy']==POLICY
    assert not observed['context']['concentracion_previa']['outside_universe_coverage_verified']


@pytest.mark.parametrize('tz',['America/Bogota','America/New_York'])
def test_year_window_not_changed_by_database_timezone(postgres_test_session,tz):
    db=postgres_test_session;db.execute(text('SELECT set_config(:key,:value,true)'),{'key':'TimeZone','value':tz})
    test_annual_sql_matches_reference(db,'boundaries')
