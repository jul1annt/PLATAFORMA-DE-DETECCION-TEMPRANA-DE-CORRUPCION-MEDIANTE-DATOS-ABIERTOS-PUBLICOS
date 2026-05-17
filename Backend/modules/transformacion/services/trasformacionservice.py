import logging
from datetime import date, datetime, timezone
from typing import Dict, List, Tuple, Any

from sqlalchemy.orm import Session

from modules.transformacion.services.normalization_service import (
    normalize_date, normalize_amount, normalize_text, generate_hash, normalize_url
)
from modules.transformacion.model.ProcesamientoLog import ProcesamientoLog
from modules.transformacion.model.ContratoProcesado import ContratoProcesado
from modules.transformacion.model.ContratoAnomaloIncompleto import ContratoAnomaloIncompleto
from modules.transformacion.repository.transformacion import TransformacionRepository
from modules.ingesta.model.RawSecop import RawSecop

logger = logging.getLogger(__name__)

# Campos cuya ausencia se considera una anomalía y debe registrarse
CAMPOS_OBLIGATORIOS = [
    "entidad",
    "nombre_del_proveedor",
    "valor_total_adjudicacion",
    "fecha_de_publicacion_del",
    "tipo_de_contrato",
]

# Fechas que se validan como no futuras (=> SOSPECHOSO)
CAMPOS_FECHA_FUTURA = [
    "fecha_de_publicacion_del",
    "fecha_adjudicacion",
    "fecha_de_ultima_publicaci",
    "fecha_de_apertura_efectiva",
]

# Montos que se validan como no negativos (=> INCOMPLETO)
CAMPOS_MONTO = [
    "precio_base",
    "valor_total_adjudicacion",
]


class TransformacionService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = TransformacionRepository(session)

    # ──────────────────────────────────────────────────────────────
    # Método principal
    # ──────────────────────────────────────────────────────────────
    def process_raw_data(self, forzar_reproceso: bool = False) -> Dict[str, Any]:
        """
        Lee registros de raw_secop, detecta anomalías, normaliza y guarda
        en contratos_procesados. Nunca modifica raw_secop.
        """
        inicio = datetime.now(timezone.utc)
        
        # Create Log
        log_entry = ProcesamientoLog(
            fecha_hora_inicio=inicio,
            estado="EN_PROCESO",
            forzar_reproceso=forzar_reproceso
        )
        self.session.add(log_entry)
        self.session.commit()
        
        chunk_size = 1000
        last_id = 0
        
        total_evaluados = 0
        procesados = 0
        omitidos = 0
        anomalias_totales = 0
        
        try:
            while True:
                # Build chunk query
                q = self.session.query(RawSecop).filter(RawSecop.id > last_id)
                
                if not forzar_reproceso:
                    q = q.outerjoin(ContratoProcesado, RawSecop.id == ContratoProcesado.raw_secop_id)\
                         .filter(ContratoProcesado.id == None)
                         
                q = q.order_by(RawSecop.id.asc()).limit(chunk_size)
                raw_records = q.all()
                
                if not raw_records:
                    break
                    
                nuevas_anomalias = []
                
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
                    
                    existente = self.repo.find_by_raw_secop_id(raw.id)
                    if existente:
                        if not forzar_reproceso:
                            omitidos += 1
                            continue
                            
                        if existente.normalized_hash == data_hash and existente.nivel_confianza == nivel_confianza and existente.es_incompleto == es_incompleto and existente.es_sospechoso == es_sospechoso:
                            omitidos += 1
                            continue
                            
                        # Actualizar el registro existente
                        for key, value in normalized.items():
                            setattr(existente, key, value)
                            
                        self.session.add(existente)
                        procesados += 1
                    else:
                        contrato = ContratoProcesado(**normalized)
                        self.session.add(contrato)
                        self.session.flush() # Flush to get ID
                        procesados += 1
                        
                        for anomalia in anomalias_registro:
                            anomalia.id_contrato_procesado = contrato.id
                        
                        nuevas_anomalias.extend(anomalias_registro)

                # Batch insert anomalias for this chunk
                if nuevas_anomalias:
                    self.repo.save_all_anomalias(nuevas_anomalias)
                    anomalias_totales += len(nuevas_anomalias)
                    self._actualizar_estadisticas(nuevas_anomalias)

                # Commit per chunk and update logs
                log_entry.total_evaluados = total_evaluados
                log_entry.procesados = procesados
                log_entry.omitidos = omitidos
                log_entry.anomalias_registradas = anomalias_totales
                log_entry.duracion_segundos = int((datetime.now(timezone.utc) - inicio).total_seconds())
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
            
            self.session.add(log_entry)
            self.session.commit()

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error en reprocesamiento: {e}", exc_info=True)
            
            fin = datetime.now(timezone.utc)
            duracion = int((fin - inicio).total_seconds())
            
            log_entry.estado = "ERROR"
            log_entry.fecha_hora_fin = fin
            log_entry.duracion_segundos = duracion
            log_entry.mensaje_error = str(e)
            
            self.session.add(log_entry)
            self.session.commit()
            
            raise e

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
    def _detectar_anomalias(self, raw: RawSecop) -> List[ContratoAnomaloIncompleto]:
        anomalias: List[ContratoAnomaloIncompleto] = []
        hoy = date.today()

        # 1. Campos obligatorios faltantes
        for campo in CAMPOS_OBLIGATORIOS:
            valor = getattr(raw, campo, None)
            if valor is None or (isinstance(valor, str) and valor.strip() == ""):
                anomalias.append(ContratoAnomaloIncompleto(
                    raw_secop_id=raw.id,
                    motivo="CAMPO_FALTANTE",
                    valor_detectado=None,
                    tipo_anomalia="CAMPO_FALTANTE",
                    valor_original=None,
                    descripcion=f"El contrato no contiene {campo}",
                    campo_afectado=campo,
                ))
                self.repo.increment_campo_faltante(campo)

        # 2. Fechas futuras => SOSPECHOSO
        for nombre_campo in CAMPOS_FECHA_FUTURA:
            valor_fecha = getattr(raw, nombre_campo, None)
            if valor_fecha is not None:
                fecha_parsed = valor_fecha.date() if isinstance(valor_fecha, datetime) else valor_fecha
                if isinstance(fecha_parsed, date) and fecha_parsed > hoy:
                    anomalias.append(ContratoAnomaloIncompleto(
                        raw_secop_id=raw.id,
                        motivo="FECHA_FUTURA",
                        valor_detectado=str(valor_fecha),
                        tipo_anomalia="FECHA_FUTURA",
                        valor_original=str(valor_fecha),
                        descripcion="El contrato contiene una fecha futura inválida",
                        campo_afectado=nombre_campo,
                    ))

        # 3. Montos negativos => INCOMPLETO
        for nombre_campo in CAMPOS_MONTO:
            monto = getattr(raw, nombre_campo, None)
            if monto is not None:
                try:
                    if float(monto) < 0:
                        anomalias.append(ContratoAnomaloIncompleto(
                            raw_secop_id=raw.id,
                            motivo="MONTO_NEGATIVO",
                            valor_detectado=str(monto),
                            tipo_anomalia="MONTO_NEGATIVO",
                            valor_original=str(monto),
                            descripcion="El contrato contiene un monto negativo",
                            campo_afectado=nombre_campo,
                        ))
                except (TypeError, ValueError):
                    pass

        return anomalias

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
            "nit_proveedor":                  normalize_text(raw.nit_del_proveedor_adjudicado),
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
    def _actualizar_estadisticas(self, anomalias: List[ContratoAnomaloIncompleto]) -> None:
        """Incrementa los contadores de estadística_campos_faltantes."""
        campos_a_incrementar: Dict[str, int] = {}
        for anomalia in anomalias:
            if anomalia.tipo_anomalia == "CAMPO_FALTANTE":
                campos_a_incrementar[anomalia.campo_afectado] = \
                    campos_a_incrementar.get(anomalia.campo_afectado, 0) + 1

        for campo, cantidad in campos_a_incrementar.items():
            for _ in range(cantidad):
                self.repo.increment_campo_faltante(campo)

        if campos_a_incrementar:
            self.session.commit()
