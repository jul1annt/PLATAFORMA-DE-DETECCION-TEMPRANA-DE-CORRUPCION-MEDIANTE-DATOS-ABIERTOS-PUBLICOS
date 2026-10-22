"""Compute public charts in the worker, then serve the frozen small payload."""
from sqlalchemy import text
from .domain import digest


class AggregatesNotReady(ValueError):
    pass


def validate_aggregates(value,revision):
    if (not isinstance(value,dict) or value.get('schema')!='citizen-aggregates-v1'
            or type(value.get('revision')) is not int or value['revision']!=revision or type(value.get('rows')) is not int or value['rows']<0
            or ('historical_high' in value and (type(value['historical_high']) is not int or not 0<=value['historical_high']<=value['rows']))
            or value.get('sha256')!=digest({k:v for k,v in value.items() if k!='sha256'})):
        raise AggregatesNotReady('Los agregados del corte no están preparados o su integridad cambió')
    distribution=value.get('risk_distribution');top=value.get('top_providers')
    if (not isinstance(distribution,list) or not isinstance(top,list) or len(top)>50
            or any(not isinstance(item,dict) or type(item.get('value')) is not int or item['value']<0 for item in distribution)
            or sum(item['value'] for item in distribution)!=value['rows']
            or any(not isinstance(item,dict) or type(item.get('contracts')) is not int or not 0<item['contracts']<=value['rows']
                   or not isinstance(item.get('nit'),str) or not item['nit'] for item in top)
            or len({item['nit'] for item in top})!=len(top)
            or sum(item['contracts'] for item in top)>value['rows']
            or top!=sorted(top,key=lambda item:(-item['contracts'],item['nit']))):
        raise AggregatesNotReady('Cobertura u orden de agregados incompatibles')
    return value


def prepare_aggregates(db,revision):
    from modules.transformacion.repository.transformacion import TransformacionRepository
    from .publication import revision_scope
    with revision_scope(db,{'revision':revision,'aggregate_build':True}):
        db.execute(text("SET LOCAL work_mem='32MB'"))
        db.execute(text('SET LOCAL max_parallel_workers_per_gather=0'))
        repo=TransformacionRepository(db)
        total=repo.get_dashboard_metricas()['total_contratos']
        historical_high=repo.count_historical_high()
        value={'schema':'citizen-aggregates-v1','revision':revision,'rows':total,
               'historical_high':historical_high,
               'risk_distribution':repo.get_risk_distribution(historical_high=historical_high,total=total),
               'top_providers':repo.get_top_providers(50)}
    value['sha256']=digest(value)
    return validate_aggregates(value,revision)


def cached_aggregates(db):
    snapshot=db.info.get('public_snapshot')
    if not snapshot or snapshot.get('aggregate_build'):
        return None
    return validate_aggregates(snapshot.get('aggregates'),snapshot['revision'])
