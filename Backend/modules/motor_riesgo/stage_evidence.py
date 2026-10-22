"""Bounded lookup of reviewed stage snapshots; never backdate a current row."""
from collections import defaultdict,Counter
from copy import deepcopy
from .domain import STAGES, digest, instant, identity_reasons, operation_key
from .models import RiskFeatureEvidence


def reviewed_stage_observations(db, rows: list, captured_at: str, evidence_root):
    """Return exact, physically verified snapshots indexed only by current batch.

    All reviews must predate the run. Multiple different reviews of one stage
    are ambiguous; never silently choose the latest or a favorable value.
    """
    from analytics_ml.evidence import validate_record
    ids=[row['id'] for row in rows]
    if not ids:return {},{}
    by_id={row['id']:row for row in rows};candidates=defaultdict(list);failures={}
    entries=db.query(RiskFeatureEvidence).filter(RiskFeatureEvidence.raw_secop_id.in_(ids),
        RiskFeatureEvidence.created_at<=instant(captured_at)).order_by(RiskFeatureEvidence.evidence_id).limit(20001).all()
    if len(entries)>20000:
        raise ValueError('Demasiadas revisiones por lote; resolver la identidad antes de preparar el corte')
    # Only reviewed operations need a unit-ambiguity lookup. Use the indexed
    # source process identity to avoid sorting every source row daily. Include
    # aliases which have not been normalized yet; they still make a call ambiguous.
    call_units,award_units=Counter(),Counter()
    if entries:
        from modules.ingesta.model.RawSecop import RawSecop as R
        processes={by_id[entry.raw_secop_id]['id_del_proceso'] for entry in entries}
        sources={by_id[entry.raw_secop_id]['fuente_id'] for entry in entries}
        aliases=db.query(R.fuente_id,R.id_del_proceso,R.id_adjudicacion).filter(
            R.id_del_proceso.in_(processes),R.fuente_id.in_(sources)).limit(20001).all()
        if len(aliases)>20000:
            raise ValueError('Demasiadas filas por operación revisada; resolver las identidades antes de inferir')
        for source,process,award in aliases:
            call_units[(source,process)]+=1;award_units[(source,process,award)]+=1
    for entry in entries:
        key=(entry.raw_secop_id,entry.stage);row=by_id[entry.raw_secop_id]
        try:
            if entry.stage not in STAGES or entry.record_sha256!=digest(entry.record) or entry.registered_by<1:
                raise ValueError('Registro de revisión inválido')
            validate_record(entry.record,evidence_root)
            observation=entry.record['observation']
            expected={'source_id':row['fuente_id'],'process_id':row['id_del_proceso'],'lot_id':None,'award_id':row['id_adjudicacion']}
            unit_rows=(award_units[(row['fuente_id'],row['id_del_proceso'],row['id_adjudicacion'])]
                       if entry.stage=='ADJUDICACION' else call_units[(row['fuente_id'],row['id_del_proceso'])])
            if unit_rows>1:
                failures[key]='identidad_operacion_ambigua'
                continue
            event=row['fecha_adjudicacion'] if entry.stage=='ADJUDICACION' else row['fecha_de_publicacion_del']
            if (observation.get('raw_secop_id')!=row['id'] or identity_reasons(observation,entry.stage)
                    or observation['source_row_id']!=row['socrata_row_id']
                    or operation_key(observation,entry.stage)!=operation_key(expected,entry.stage)
                    or entry.prediction_at!=instant(observation['prediction_at'])
                    or event is None or instant(event.isoformat())!=entry.prediction_at
                    or entry.prediction_at>instant(captured_at) or unit_rows!=1):
                raise ValueError('La identidad o fecha de etapa difieren de la fuente conservada')
            candidates[key].append((entry.evidence_id,observation))
        except (KeyError,ValueError,TypeError,OSError,OverflowError,AttributeError):
            failures[key]='evidencia_de_etapa_no_verificable'
    verified={}
    for key,records in candidates.items():
        if key in failures:continue
        if len({digest(item) for _,item in records})!=1:
            failures[key]='revisiones_de_etapa_en_conflicto';continue
        evidence_id,observation=records[0]
        verified[key]={**deepcopy(observation),'feature_evidence_id':evidence_id}
    return verified,failures
