"""Pure snapshot-to-feature mapping shared by capture checks and model inputs."""
import math
import unicodedata
from .domain import NUMERIC, digest, instant, secop_source_url, official_id
from .method_reference import CONTEXT_POLICY
from .annual_context import POLICY as ANNUAL_POLICY, buyer_key


def nonnegative_number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) and number >= 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def capture_stage(row: dict, at: str) -> tuple[str | None, str | None]:
    now = instant(at)
    award_status = str(row['adjudicado'] or '').strip().upper()
    if award_status not in {'SI', 'SÍ', 'TRUE', '1', 'NO', 'FALSE', '0'}:
        return None, 'etapa_sin_confirmar'
    awarded = award_status in {'SI', 'SÍ', 'TRUE', '1'}
    state = ''.join(c for c in unicodedata.normalize('NFKD', str(row['estado_del_procedimiento'] or '').upper()) if not unicodedata.combining(c))
    if state in {'CANCELADO', 'SUSPENDIDO', 'BORRADOR', 'EN APROBACION'}:
        return None, 'estado_fuera_del_alcance'
    if not awarded and state not in {'PUBLICADO', 'ABIERTO', 'EVALUACION'}:
        return None, 'etapa_sin_confirmar'
    stage = 'ADJUDICACION' if awarded else 'CONVOCATORIA'
    published = row['fecha_de_publicacion_del']
    stage_date = row['fecha_adjudicacion'] if awarded else published
    if ((stage_date is not None and (stage_date.tzinfo is None or stage_date > now))
            or (published is not None and (published.tzinfo is None or published > now))):
        return None, 'fecha_etapa_futura_o_invalida'
    return stage, None


def build_observation(row: dict, at: str) -> dict | None:
    """Capture current knowledge without pretending it is a historic snapshot."""
    stage, reason = capture_stage(row, at)
    if reason:
        return None
    now = instant(at)
    awarded = stage == 'ADJUDICACION'
    published = row['fecha_de_publicacion_del']
    stage_date = row['fecha_adjudicacion'] if awarded else published
    snapshot = {k: str(v) if v is not None else None for k, v in row.items()}
    snapshot_hash = digest(snapshot)
    values = {'categoria': row['codigo_principal_de_categoria'], 'modalidad': row['modalidad_de_contratacion'],
              'departamento': row['departamento_entidad']}
    quality_reasons = ['fecha_etapa_ausente'] if stage_date is None else []
    annual_identity = (type(row.get('fuente_id')) is int and row['fuente_id']>0
                       and type(row.get('unit_rows')) is int and row['unit_rows']==1
                       and buyer_key(row.get('nit_entidad'))
                       and all(official_id(row.get(key)) for key in ('socrata_row_id','id_del_proceso'))
                       and (buyer_key(row.get('raw_buyer_key')) is None
                            or buyer_key(row['raw_buyer_key'])==buyer_key(row['nit_entidad'])))
    if annual_identity and row.get('annual_policy') == ANNUAL_POLICY:
        if row.get('buyer_previous') is not None:
            values['procesos_previos'] = int(row['buyer_previous'])
        concentration = nonnegative_number(row.get('concentration'))
        if row.get('market_complete') and concentration is not None and concentration<=1:
            values['concentracion_previa'] = concentration
    rolling_identity = (stage == 'ADJUDICACION' and row.get('unit_rows') == 1
                        and all(official_id(row.get(key)) for key in
                                ('nit_entidad', 'nit_proveedor_clave', 'socrata_row_id', 'id_del_proceso', 'id_adjudicacion'))
                        and all(str(row.get(key)).strip() not in {'0', '-'} for key in ('nit_entidad','nit_proveedor_clave')))
    if rolling_identity and row.get('rolling_policy') == CONTEXT_POLICY:
        if row.get('repeated') is not None and official_id(row.get('codigo_principal_de_categoria')):
            values['reiteraciones_30d'] = int(row['repeated'])
        if row.get('direct90') is not None:
            values['directas_90d'] = int(row['direct90'])
    if row['duracion'] is not None and str(row['unidad_de_duracion'] or '').strip().lower() in {'dia','dias','día','días','dia(s)','día(s)'}:
        number = nonnegative_number(row['duracion'])
        if number is not None:
            values['duracion_dias'] = number
        else:
            quality_reasons.append('dato_invalido:duracion_dias')
    for field, amount in (('log_presupuesto', row['precio_base']), ('log_adjudicado', row['valor_total_adjudicacion'])):
        if field in NUMERIC[stage] and amount is not None:
            number = nonnegative_number(amount)
            if number is not None and number > 0:
                values[field] = math.log1p(number)
            else:
                quality_reasons.append('dato_invalido:' + field)
    return {'stage': stage, 'raw_secop_id': row['id'], 'source_id': row['fuente_id'],
        'source_row_id': row['socrata_row_id'], 'process_id': row['id_del_proceso'],
        'award_id': row['id_adjudicacion'] if awarded else None, 'lot_id': None,
        'identity_ambiguous': (row.get('unit_rows') or 1) > 1,
        'capture_reasons': quality_reasons,
        'supplier_group': row['nit_proveedor_clave'] if awarded else None, 'buyer_group': row['nit_entidad'],
        'prediction_at': now.isoformat(), 'snapshot': snapshot, 'snapshot_sha256': snapshot_hash,
        'stage_event_at': stage_date.isoformat() if stage_date is not None else None,
        'fields': {n: {'value': v, 'available_at': now.isoformat(), 'sha256': snapshot_hash} for n, v in values.items() if v is not None},
        'observed': {'budget': str(row['precio_base']) if row['precio_base'] is not None else None,
                     'awarded_amount': str(row['valor_total_adjudicacion']) if awarded and row['valor_total_adjudicacion'] is not None else None,
                     'modality': row['modalidad_de_contratacion'], 'direct_justification': row.get('justificaci_n_modalidad_de')},
        'context': {'directas_90d': {'processes': values.get('directas_90d'),
                    'amount': None, 'amounts_complete': False, 'amount_reason': 'moneda_no_documentada_en_fuente_local',
                    'unit': 'importe no evaluado; excluye el proceso actual'},
                    'rolling': {'policy': row.get('rolling_policy'), 'anchor_at': now.isoformat(),
                                'anchor_semantics': 'capture_time_not_historical_award',
                                'universe': 'known_normalized_pairs_in_selected_source_capture',
                                'outside_universe_coverage_verified': False,
                                'target_identity_verified': bool(rolling_identity),
                                'bad_rows_30d': int(row.get('rolling_bad30') or 0) if row.get('rolling_policy') == CONTEXT_POLICY else None,
                                'bad_rows_90d': int(row.get('rolling_bad90') or 0) if row.get('rolling_policy') == CONTEXT_POLICY else None,
                                'observed_repeated_processes': row.get('rolling_observed_repeat'),
                                'observed_direct_processes': row.get('rolling_observed_direct')},
                    'concentracion_previa': {'processes': row.get('market_processes'),
                        'complete': bool(annual_identity and row.get('annual_policy')==ANNUAL_POLICY and row.get('market_complete')),
                        'policy': row.get('annual_policy'), 'anchor_at':now.isoformat(),
                        'metric':'maximum_supplier_process_participation_not_monetary_share_or_hhi',
                        'max_supplier_processes':row.get('annual_maximum'),
                        'bad_market_rows':int(row.get('annual_bad_market') or 0) if row.get('annual_policy')==ANNUAL_POLICY else None,
                        'bad_publication_rows':int(row.get('annual_bad_pub') or 0) if row.get('annual_policy')==ANNUAL_POLICY else None,
                        'target_process_excluded':True, 'outside_universe_coverage_verified':False}},
        'source_url': secop_source_url(row['urlproceso']), 'temporal_scope': 'observed_at_capture_not_backdated'}
