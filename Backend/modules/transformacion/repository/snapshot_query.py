"""Bound each ordered version branch before the final page merge.

The global first k rows of a union are contained in the first k rows of each
branch under the same total ordering. Version ranges are disjoint by ID, and
the ID breaks sort ties. This avoids sorting the entire multi-million-row view.
"""
from functools import lru_cache
from sqlalchemy import MetaData,Column,BigInteger,union_all
from sqlalchemy.orm import aliased
from modules.transformacion.model.ContratoProcesado import ContratoProcesado


@lru_cache(maxsize=1)
def version_models():
    current=ContratoProcesado.__table__.to_metadata(MetaData(),schema='public')
    historical=ContratoProcesado.__table__.to_metadata(MetaData(),schema='riesgo_historial')
    historical.append_column(Column('riesgo_hasta_revision',BigInteger))
    return (aliased(ContratoProcesado,current,adapt_on_names=True),
            aliased(ContratoProcesado,historical,adapt_on_names=True),historical)


def snapshot_page(repository,filters,revision,skip,limit,sort,order):
    current,historical,table=version_models()
    branches=[]
    for model in (current,historical):
        query=repository._filtered_contracts(model,filters).filter(model.riesgo_desde_revision<=revision)
        if model is historical:
            query=query.filter(table.c.riesgo_hasta_revision>revision)
        branches.append(repository._ordered_contracts(query,model,sort,order).limit(skip+limit).statement)
    combined=union_all(*branches).subquery()
    model=aliased(ContratoProcesado,combined,adapt_on_names=True)
    query=repository._ordered_contracts(repository.session.query(model),model,sort,order)
    return query.offset(skip).limit(limit).all()
