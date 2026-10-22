"""Commit result batches and their durable position in the same transaction."""
import json
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from analytics_ml.streams import binary_stream
from .domain import STAGES
from .models import RiskCut,RiskResult


def persist_results(db,cut_id,output,manifest,*,batch_size=1000):
    if type(batch_size) is not int or not 1<=batch_size<=1000:
        raise ValueError('El lote de persistencia debe contener entre 1 y 1000 filas')
    cut=db.get(RiskCut,cut_id)
    saved=cut.context.get('persistence_checkpoint')
    counts={s:0 for s in STAGES}
    position=0
    if saved is not None:
        if (saved.get('output_sha256')!=manifest['output_sha256']
                or type(saved.get('lines')) is not int or not 0<=saved['lines']<=manifest['input_rows']
                or set(saved.get('counts',{}))!=set(STAGES)
                or any(type(n) is not int or n<0 for n in saved['counts'].values())
                or sum(saved['counts'].values())!=saved['lines']):
            raise ValueError('El cursor de persistencia no corresponde al resultado verificado')
        position=saved['lines'];counts=dict(saved['counts'])
    persisted={stage:count for stage,count in db.query(RiskResult.stage,func.count()).filter_by(cut_id=cut_id).group_by(RiskResult.stage)}
    if {stage:persisted.get(stage,0) for stage in STAGES}!=counts or set(persisted)-set(STAGES):
        raise ValueError('Los resultados confirmados difieren del cursor durable')
    lines=0;batch=[]
    def commit_batch():
        nonlocal cut,batch
        # A conflict here indicates corruption or overlapping workers. Do not
        # hide it with DO NOTHING and advance past a different result.
        # Bind one Core INSERT template for the batch. Building a new SQL
        # expression with thousands of individually named values per batch
        # spends most of the writer's CPU compiling equivalent statements.
        db.execute(insert(RiskResult.__table__),batch)
        cut=db.get(RiskCut,cut_id)
        cut.context={**cut.context,'persistence_checkpoint':{'output_sha256':manifest['output_sha256'],
            'lines':lines,'counts':dict(counts)}}
        db.commit();batch=[]
    with binary_stream(output,'rb') as source:
        for line in source:
            lines+=1
            if lines<=position:continue
            record=json.loads(line)
            if record.get('stage') not in STAGES or type(record.get('raw_secop_id')) is not int or record['raw_secop_id']<1:
                raise ValueError('Identidad o etapa del resultado inválida')
            if set(record)!={'raw_secop_id','stage','result'}:
                raise ValueError('Estructura de resultado inválida')
            counts[record['stage']]+=1
            if counts[record['stage']]>manifest['counts'][record['stage']]:
                raise ValueError('El resultado excede la cobertura de su etapa')
            batch.append({'cut_id':cut_id,**record})
            if len(batch)==batch_size:commit_batch()
        if batch:commit_batch()
    if counts!=manifest['counts'] or lines!=manifest['input_rows']:
        raise ValueError('Inferencia incompleta al persistir')
    return counts
