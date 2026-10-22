"""Read-only check of privileges required by the complete daily pipeline."""
from sqlalchemy import text


def missing_runtime_permissions(db):
    from .publication import TABLES
    requirements=[]
    def need(kind,name,privileges):
        requirements.extend((kind,name,privilege) for privilege in privileges)
    for schema in ('public','riesgo_historial','riesgo_ciudadano'):
        need('schema',schema,['USAGE'])
    for table in TABLES:
        need('table','public.'+table,['SELECT','INSERT','UPDATE','DELETE'])
        need('table','riesgo_historial.'+table,['SELECT','INSERT'])
        need('table','riesgo_ciudadano.'+table,['SELECT'])
    need('table','public.raw_secop',['SELECT','INSERT','UPDATE'])
    # The parent pipeline dispatches durable children. Ingestion also updates
    # its cursor/source state and retains before images; checking analytical
    # tables alone would approve a worker that cannot complete its first step.
    need('table','public.background_jobs',['SELECT','INSERT','UPDATE'])
    need('table','public.fuentes_datos',['SELECT','UPDATE'])
    need('table','public.raw_secop_historial',['SELECT','INSERT'])
    need('table','public.sincronizacion_historial',['SELECT','INSERT','UPDATE'])
    need('table','public.riesgo_versiones_datos',['SELECT','UPDATE'])
    for table in ('riesgo_publicacion','riesgo_publicacion_ciudadana','riesgo_cortes','riesgo_cortes_ciudadanos'):
        need('table','public.'+table,['SELECT','INSERT','UPDATE'])
    for table in ('riesgo_resultados','riesgo_modelos','riesgo_casos','riesgo_evidencias_variables','riesgo_auditoria'):
        need('table','public.'+table,['SELECT','INSERT'])
    need('sequence','public.riesgo_revision_ciudadana',['USAGE','SELECT'])
    for table in (*TABLES,'raw_secop','raw_secop_historial',
                  'sincronizacion_historial','background_jobs',
                  'riesgo_resultados','riesgo_auditoria'):
        sequence=db.execute(text('SELECT pg_get_serial_sequence(:table_name,\'id\')'),{'table_name':'public.'+table}).scalar_one()
        if sequence:need('sequence',sequence,['USAGE','SELECT'])
    missing=[]
    for kind,name,privilege in requirements:
        # Function names are selected from these fixed internal constants.
        allowed=db.execute(text('SELECT has_'+kind+'_privilege(current_user,:name,:privilege)'),{'name':name,'privilege':privilege}).scalar_one()
        if not allowed:missing.append({'kind':kind,'object':name,'privilege':privilege})
    return missing
