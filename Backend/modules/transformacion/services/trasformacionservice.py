import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from modules.transformacion.services.normalization_service import (
    normalize_date, normalize_amount, normalize_text, normalize_provider_nit,
    normalize_provider_nit_identity, detect_anomalies,
    generate_hash, normalize_url
)
from modules.transformacion.model.ProcesamientoLog import ProcesamientoLog
from modules.transformacion.model.ContratoProcesado import ContratoProcesado
from modules.transformacion.repository.transformacion import TransformacionRepository
from modules.ingesta.model.RawSecop import RawSecop

logger = logging.getLogger(__name__)
VERSION_REGLAS_TRANSFORMACION = "v1.0"

class TransformacionService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = TransformacionRepository(session)

    # ──────────────────────────────────────────────────────────────
    # Método principal
    # ──────────────────────────────────────────────────────────────
    def process_raw_data(
        self, forzar_reproceso: bool = False, job_id: int | None = None,
    ) -> Dict[str, Any]:
        """
        Lee registros de raw_secop, detecta anomalías, normaliza y guarda
        en contratos_procesados. Nunca modifica raw_secop.
        """
        inicio = datetime.now(timezone.utc)
        chunk_size = 1000
        universo: Dict[str, Any] = {
            "forzar_reproceso": bool(forzar_reproceso),
            "tamano_lote": chunk_size,
            "max_raw_secop_id": 0,
            "total_candidatos": 0,
            "total_evaluados": 0,
            "ultimo_raw_secop_id": 0,
        }
        if job_id is not None:
            universo["background_job_id"] = job_id
        
        # Create Log
        log_entry = ProcesamientoLog(
            fecha_hora_inicio=inicio,
            estado="EN_PROCESO",
            forzar_reproceso=forzar_reproceso,
            version_reglas=VERSION_REGLAS_TRANSFORMACION,
            universo=dict(universo),
        )
        self.session.add(log_entry)
        self.session.commit()
        
        last_id = 0
        
        total_evaluados = 0
        procesados = 0
        omitidos = 0
        anomalias_totales = 0
        
        try:
            universo.update(self.repo.obtener_universo_reprocesamiento(forzar_reproceso))
            log_entry.universo = dict(universo)
            self.session.add(log_entry)
            self.session.commit()

            while True:
                # Build chunk query
                q = self.session.query(RawSecop).filter(
                    RawSecop.id > last_id,
                    RawSecop.id <= universo["max_raw_secop_id"],
                )
                
                if not forzar_reproceso:
                    q = q.outerjoin(
                        ContratoProcesado,
                        and_(
                            RawSecop.id == ContratoProcesado.raw_secop_id,
                            # Keep the processed side inside this keyset window.
                            # Otherwise PostgreSQL may rescan its entire index for
                            # every 1000-row batch.
                            ContratoProcesado.raw_secop_id > last_id,
                            ContratoProcesado.raw_secop_id <= universo["max_raw_secop_id"],
                        ),
                    ).filter(or_(
                        ContratoProcesado.id.is_(None),
                        RawSecop.sincronizado_en > ContratoProcesado.procesado_en,
                    ))
                         
                q = q.order_by(RawSecop.id.asc()).limit(chunk_size)
                raw_records = q.all()
                
                if not raw_records:
                    break

                contratos_existentes = self.repo.obtener_contratos_por_raw_ids(
                    [raw.id for raw in raw_records]
                )
                contratos_nuevos = []
                reemplazos_anomalias = []

                for raw in raw_records:
                    total_evaluados += 1
                    
                    if raw.id > last_id:
                        last_id = raw.id
                        
                    # Normalizar
                    normalized = self._normalizar(raw)
                    data_hash = generate_hash(normalized)

                    anomalias_registro = self._detectar_anomalias(raw)
                    
                    campos_faltantes = [
                        a.campo_afectado for a in anomalias_registro 
                        if a.tipo_anomalia == "CAMPO_FALTANTE"
                    ]
                    tiene_monto_negativo = any(
                        a.tipo_anomalia == "MONTO_NEGATIVO" for a in anomalias_registro
                    )
                    tiene_fecha_futura = any(
                        a.tipo_anomalia == "FECHA_FUTURA" for a in anomalias_registro
                    )
                    
                    cantidad_faltantes = len(campos_faltantes)
                    es_incompleto = cantidad_faltantes > 0 or tiene_monto_negativo
                    es_sospechoso = tiene_fecha_futura
                    
                    nivel_confianza = 100
                    if cantidad_faltantes > 0:
                        nivel_confianza -= (cantidad_faltantes * 20)
                    if tiene_monto_negativo:
                        nivel_confianza -= 20
                    if es_sospechoso:
                        nivel_confianza -= 40
                        
                    nivel_confianza = max(0, min(100, nivel_confianza))

                    normalized["normalized_hash"] = data_hash
                    normalized["es_incompleto"] = es_incompleto
                    normalized["es_sospechoso"] = es_sospechoso
                    normalized["cantidad_campos_faltantes"] = cantidad_faltantes
                    normalized["campos_faltantes"] = campos_faltantes
                    normalized["nivel_confianza"] = nivel_confianza
                    
                    existente = contratos_existentes.get(raw.id)
                    if existente:
                        sin_cambios = (
                            existente.normalized_hash == data_hash
                            and existente.nivel_confianza == nivel_confianza
                            and existente.es_incompleto == es_incompleto
                            and existente.es_sospechoso == es_sospechoso
                        )
                        if sin_cambios:
                            omitidos += 1
                        else:
                            for key, value in normalized.items():
                                setattr(existente, key, value)
                            existente.clasificacion_riesgo = "SIN_EVALUAR"
                            existente.score_riesgo = None
                            existente.riesgo_run_id = None
                            self.session.add(existente)
                            procesados += 1
                        existente.procesado_en = datetime.now(timezone.utc)
                        reemplazos_anomalias.append(
                            (existente.id, raw.id, anomalias_registro)
                        )
                        anomalias_totales += len(anomalias_registro)
                    else:
                        contrato = ContratoProcesado(**normalized)
                        self.session.add(contrato)
                        contratos_nuevos.append(
                            (contrato, raw.id, anomalias_registro)
                        )
                        anomalias_totales += len(anomalias_registro)

                if contratos_nuevos:
                    # One flush assigns all generated contract IDs before the
                    # anomaly history is reconciled for the complete chunk.
                    self.session.flush()
                    procesados += len(contratos_nuevos)
                    reemplazos_anomalias.extend(
                        (contrato.id, raw_id, hallazgos)
                        for contrato, raw_id, hallazgos in contratos_nuevos
                    )
                self.repo.replace_anomalias_batch(
                    reemplazos_anomalias,
                    nuevos_raw_ids={raw_id for _contrato, raw_id, _ in contratos_nuevos},
                )

                # Commit per chunk and update logs
                log_entry.total_evaluados = total_evaluados
                log_entry.procesados = procesados
                log_entry.omitidos = omitidos
                log_entry.anomalias_registradas = anomalias_totales
                log_entry.duracion_segundos = int((datetime.now(timezone.utc) - inicio).total_seconds())
                universo.update({
                    "total_evaluados": total_evaluados,
                    "ultimo_raw_secop_id": last_id,
                })
                log_entry.universo = dict(universo)
                self.session.add(log_entry)
                self.session.commit()
                
                # Cleanup identity map to prevent memory leak
                for raw in raw_records:
                    self.session.expunge(raw)
                
            # Done with all chunks
            self.repo.recalculate_porcentajes_estadisticas_campos()
            self.session.commit()
            
            # Update Log success
            fin = datetime.now(timezone.utc)
            duracion = int((fin - inicio).total_seconds())
            
            log_entry.estado = "EXITOSO"
            log_entry.fecha_hora_fin = fin
            log_entry.duracion_segundos = duracion
            log_entry.total_evaluados = total_evaluados
            log_entry.procesados = procesados
            log_entry.omitidos = omitidos
            log_entry.anomalias_registradas = anomalias_totales
            universo.update({
                "total_evaluados": total_evaluados,
                "ultimo_raw_secop_id": last_id,
            })
            log_entry.universo = dict(universo)
            
            self.session.add(log_entry)
            self.session.commit()

        except Exception as exc:
            self.session.rollback()
            error_id = str(uuid.uuid4())
            try:
                # Earlier chunks are committed independently. Rebuild the
                # aggregate from their persisted current anomalies before
                # recording the failed run, so a partial failure does not
                # leave field counts behind the contracts that were saved.
                self.repo.recalculate_porcentajes_estadisticas_campos()
                self.session.commit()
            except Exception as stats_exc:
                self.session.rollback()
                logger.error(
                    "No se pudieron reconciliar estadísticas tras reprocesamiento fallido; "
                    "referencia=%s tipo=%s",
                    error_id,
                    type(stats_exc).__name__,
                )
            logger.error(
                "Error en reprocesamiento; referencia=%s tipo=%s",
                error_id,
                type(exc).__name__,
            )
            
            fin = datetime.now(timezone.utc)
            duracion = int((fin - inicio).total_seconds())
            
            log_entry.estado = "ERROR"
            log_entry.fecha_hora_fin = fin
            log_entry.duracion_segundos = duracion
            log_entry.mensaje_error = f"Error interno {error_id}"
            universo.update({
                "total_evaluados": total_evaluados,
                "ultimo_raw_secop_id": last_id,
            })
            log_entry.universo = dict(universo)
            
            self.session.add(log_entry)
            self.session.commit()
            
            raise

        return {
            "total_evaluados": total_evaluados,
            "procesados": procesados,
            "omitidos": omitidos,
            "anomalias_registradas": anomalias_totales,
            "fecha_hora_inicio": inicio,
            "fecha_hora_fin": fin,
            "duracion_segundos": duracion,
            "estado": "EXITOSO"
        }

    # ──────────────────────────────────────────────────────────────
    # Detección de anomalías
    # ──────────────────────────────────────────────────────────────
    def _detectar_anomalias(self, raw: RawSecop):
        # La regla de negocio produce hallazgos inmutables; el repositorio los
        # materializa como filas solamente al guardar o reconciliar anomalías.
        return detect_anomalies(
            raw.__dict__,
            raw_secop_id=raw.id,
            current_date=datetime.now(timezone.utc).date(),
        )

    # ──────────────────────────────────────────────────────────────
    # Normalización — nombres de columnas reales de raw_secop
    # ──────────────────────────────────────────────────────────────
    def _normalizar(self, raw: RawSecop) -> Dict[str, Any]:
        return {
            "raw_secop_id":                  raw.id,
            "id_del_proceso":                normalize_text(raw.id_del_proceso),
            "entidad_normalizada":            normalize_text(raw.entidad),
            "nit_entidad":                    normalize_text(raw.nit_entidad),
            "proveedor_normalizado":          normalize_text(raw.nombre_del_proveedor),
            "nit_proveedor":                  normalize_provider_nit(raw.nit_del_proveedor_adjudicado),
            "nit_proveedor_clave":             normalize_provider_nit_identity(raw.nit_del_proveedor_adjudicado),
            "fecha_publicacion_normalizada":  normalize_date(raw.fecha_de_publicacion_del),
            "fecha_adjudicacion_normalizada": normalize_date(raw.fecha_adjudicacion),
            "valor_total_normalizado":        normalize_amount(raw.valor_total_adjudicacion),
            "precio_base_normalizado":        normalize_amount(raw.precio_base),
            "tipo_contrato_normalizado":      normalize_text(raw.tipo_de_contrato),
            "modalidad_contratacion":         normalize_text(raw.modalidad_de_contratacion),
            "estado_normalizado":             normalize_text(raw.estado_del_procedimiento),
            "ciudad_entidad":                 normalize_text(raw.ciudad_entidad),
            "departamento_entidad":           normalize_text(raw.departamento_entidad),
            "urlproceso":                     normalize_url(raw.urlproceso),
        }

    # ──────────────────────────────────────────────────────────────
    # Estadísticas de campos faltantes
    # ──────────────────────────────────────────────────────────────
