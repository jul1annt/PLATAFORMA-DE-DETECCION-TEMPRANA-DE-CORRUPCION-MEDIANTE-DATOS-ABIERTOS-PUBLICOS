"""Definitions, units, eligibility and limits form part of the public methodology."""
from .domain import REFERENCES

INDICATORS = [
    {'id': 'IMPORTE_ATIPICO', 'stage': ['CONVOCATORIA','ADJUDICACION'], 'unit': 'operacion',
     'formula': 'valor < Q1-1.5*(Q3-Q1) o valor > Q3+1.5*(Q3-Q1)',
     'requires': ['importe positivo','categoria','modalidad','periodo','30 observaciones comparables no ambiguas','IQR positivo'],
     'source': REFERENCES['ocp'], 'limits': 'Importes totales no son precios unitarios. No acredita sobreprecio.'},
    {'id': 'REITERACION_30D', 'stage': ['ADJUDICACION'], 'unit': 'entidad/proveedor/categoria',
     'formula': 'procesos distintos de la misma entidad, proveedor y categoria en [t-30d,t], excluyendo el actual',
     'requires': ['identidad entidad','clave proveedor','identidad proceso/adjudicacion no ambigua','categoria','fecha adjudicacion','historia suficiente'],
     'development_threshold': 2,
     'source': REFERENCES['colombia'], 'limits': 'Heurística contextual del proyecto; reiteración no acredita duplicación ni fraccionamiento.'},
    {'id': 'DIRECTAS_90D', 'stage': ['ADJUDICACION'], 'unit': 'entidad/proveedor',
     'formula': 'procesos directos distintos en [t-2160h,t], excluyendo todo el proceso objetivo',
     'requires': ['identidad entidad','clave proveedor','identidad proceso/adjudicacion no ambigua','modalidad verificada','fecha adjudicacion','historia suficiente'],
     'development_threshold': 3,
     'source': REFERENCES['colombia'], 'limits': 'Contratación directa tiene causales legales; revisar justificación. 90 días es parámetro operativo.'},
    {'id': 'CONCENTRACION_PREVIA', 'stage': ['CONVOCATORIA','ADJUDICACION'], 'unit': 'entidad',
     'formula': 'maximo de procesos distintos por proveedor / procesos distintos adjudicados de entidad en [t-8760h,t], excluyendo todo el proceso objetivo',
     'requires': ['identidad entidad','proveedores e identidades comprobables','fechas de adjudicacion','denominador completo y no vacio en el marco declarado'],
     'source': REFERENCES['cri'], 'source_role': 'motivacion_metodologica_no_validacion_de_formula_local',
     'limits': 'Participacion en procesos; no cuota monetaria ni HHI. Datos desconocidos impiden una razon sobre el subconjunto conocido. No aporta un punto adicional a la referencia de familias.'},
    {'id': 'OFERENTE_UNICO', 'stage': ['ADJUDICACION'], 'unit': 'proceso competitivo',
     'formula': 'numero de oferentes unicos=1, exclusivamente en modalidad competitiva',
     'requires': ['ofertas presentadas acreditadas','ambito por lote o adjudicacion comprobado','modalidad competitiva'],
     'source': REFERENCES['ocp'], 'limits': 'Los contadores SECOP auditados de respuestas, invitaciones e interes no acreditan oferentes reales. No se habilita sustitucion automatica.'},
    {'id': 'PLAZO_OFERTAS', 'stage': ['CONVOCATORIA'], 'unit': 'proceso',
     'formula': '(fecha limite de ofertas - publicacion)/86400 segundos',
     'requires': ['diccionario validado de fecha limite','publicacion','zona horaria'],
     'source': REFERENCES['cri'], 'limits': 'Sin umbral jurídico universal. Deshabilitado en captura automática hasta validar semántica.'},
]


def development_reference():
    """Public disclosure derived from actual family definitions, without DB reads."""
    from .baseline_coverage import baseline_coverage, NOT_APPLICABLE
    from .annual_context import POLICY as annual_policy
    from .method_reference import CONTEXT_POLICY
    from .robust_priority import methodology as priority_methodology
    award = baseline_coverage({}, 'ADJUDICACION')
    return {'policy_version': 'base-analitica-pesos-v8', 'intended_use': 'referencia_descriptiva_de_desarrollo',
            'coverage_policy': award['policy'],
            'family_weights': {name: value['weight'] for name,value in award['families'].items()},
            'family_indicators': {name: value['indicators'] for name,value in award['families'].items()},
            'families_by_stage': {stage:[name for name,value in baseline_coverage({},stage)['families'].items()
                                         if value['status']!=NOT_APPLICABLE] for stage in ('CONVOCATORIA','ADJUDICACION')},
            'weights_calibrated': False, 'maximum_contribution_per_family': 1,
            'score_semantics': 'conteo_de_familias_confirmadas_con_cobertura_separada',
            'complete_count_certifies_all_indicators': False,
            'missing_data_is_zero': False, 'reference_index_0_100': False, 'corruption_probability': False,
            'legacy_provider_score_is_separate': True,
            'rolling_policy': CONTEXT_POLICY, 'annual_context_policy': annual_policy,
            'priority_analysis': priority_methodology(),
            'annual_context_is_extra_family_point': False,
            'automatic_response_counter_to_bidder_mapping': False,
            'historical_training_from_current_cut_allowed': False}
