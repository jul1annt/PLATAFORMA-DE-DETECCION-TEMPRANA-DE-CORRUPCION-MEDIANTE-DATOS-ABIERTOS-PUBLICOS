import logging
from datetime import date, datetime
from typing import Dict, List, Tuple, Any

from sqlalchemy.orm import Session

from modules.transformacion.services.normalization_service import (
    normalize_date, normalize_amount, normalize_text, generate_hash
)
from modules.transformacion.model.ContratoProcesado import ContratoProcesado
from modules.transformacion.model.ContratoAnomaloIncompleto import ContratoAnomaloIncompleto
from modules.transformacion.repository.transformacion import TransformacionRepository
from modules.ingesta.model.RawSecop import RawSecop

logger = logging.getLogger(__name__)

# Campos cuya ausencia se considera una anomalía y debe registrarse
CAMPOS_OBLIGATORIOS = [
    "id_del_proceso",
    "entidad",
    "nit_entidad",
    "fecha_de_publicacion_del",
    "tipo_de_contrato",
    "estado_del_procedimiento",
    "nombre_del_proveedor",
    "valor_total_adjudicacion",
]

# Fechas que se validan como no futuras
CAMPOS_FECHA = [
    ("fecha_de_publicacion_del",  "fecha_publicacion_normalizada"),
    ("fecha_adjudicacion",         "fecha_adjudicacion_normalizada"),
    ("fecha_de_ultima_publicaci",  None),   # Solo se valida, no se guarda
]


class TransformacionService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = TransformacionRepository(session)

    # ──────────────────────────────────────────────────────────────
    # Método principal
    # ──────────────────────────────────────────────────────────────
    def process_raw_data(self, limite: int = 1000, forzar_reproceso: bool = False) -> Dict[str, int]:
        """
        Lee registros de raw_secop, detecta anomalías, normaliza y guarda
        en contratos_procesados. Nunca modifica raw_secop.
        """
        query = self.session.query(RawSecop)

        if not forzar_reproceso:
            subquery = self.session.query(ContratoProcesado.raw_secop_id).subquery()
            query = query.filter(~RawSecop.id.in_(subquery))

        raw_records = query.limit(limite).all()

        nuevos_contratos: List[ContratoProcesado] = []
        nuevas_anomalias: List[ContratoAnomaloIncompleto] = []
        procesados = 0
        omitidos = 0

        for raw in raw_records:
            anomalias_registro = self._detectar_anomalias(raw)
            nuevas_anomalias.extend(anomalias_registro)

            # Normalizar todos los campos independientemente de si hay anomalías
            normalized = self._normalizar(raw)
            data_hash = generate_hash(normalized)

            # Evitar duplicados por hash
            if forzar_reproceso and self.repo.find_by_hash(data_hash):
                omitidos += 1
                continue

            normalized["normalized_hash"] = data_hash
            nuevos_contratos.append(ContratoProcesado(**normalized))
            procesados += 1

            # Batch insert
            if len(nuevos_contratos) >= 500:
                self.repo.save_all_contratos(nuevos_contratos)
                nuevos_contratos = []

        # Guardar remanentes
        if nuevos_contratos:
            self.repo.save_all_contratos(nuevos_contratos)

        # Guardar anomalías en batch
        if nuevas_anomalias:
            self.repo.save_all_anomalias(nuevas_anomalias)

        # Actualizar estadísticas de campos faltantes
        self._actualizar_estadisticas(nuevas_anomalias)

        return {
            "total_evaluados": len(raw_records),
            "procesados": procesados,
            "omitidos": omitidos,
            "anomalias_registradas": len(nuevas_anomalias),
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
            if valor is None or str(valor).strip() == "":
                anomalias.append(ContratoAnomaloIncompleto(
                    raw_secop_id=raw.id,
                    motivo="CAMPO_FALTANTE",
                    campo_afectado=campo,
                    valor_detectado=None,
                ))
                self.repo.increment_campo_faltante(campo)

        # 2. Fechas futuras
        fechas_a_validar = [
            ("fecha_de_publicacion_del",  raw.fecha_de_publicacion_del),
            ("fecha_adjudicacion",         raw.fecha_adjudicacion),
            ("fecha_de_ultima_publicaci",  raw.fecha_de_ultima_publicaci),
        ]
        for nombre_campo, valor_fecha in fechas_a_validar:
            if valor_fecha is not None:
                fecha_parsed = valor_fecha.date() if isinstance(valor_fecha, datetime) else valor_fecha
                if isinstance(fecha_parsed, date) and fecha_parsed > hoy:
                    anomalias.append(ContratoAnomaloIncompleto(
                        raw_secop_id=raw.id,
                        motivo="FECHA_FUTURA",
                        campo_afectado=nombre_campo,
                        valor_detectado=str(valor_fecha),
                    ))

        # 3. Montos negativos
        montos_a_validar = [
            ("precio_base",              raw.precio_base),
            ("valor_total_adjudicacion", raw.valor_total_adjudicacion),
        ]
        for nombre_campo, monto in montos_a_validar:
            if monto is not None:
                try:
                    if float(monto) < 0:
                        anomalias.append(ContratoAnomaloIncompleto(
                            raw_secop_id=raw.id,
                            motivo="MONTO_NEGATIVO",
                            campo_afectado=nombre_campo,
                            valor_detectado=str(monto),
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
            "urlproceso":                     raw.urlproceso,
        }

    # ──────────────────────────────────────────────────────────────
    # Estadísticas de campos faltantes
    # ──────────────────────────────────────────────────────────────
    def _actualizar_estadisticas(self, anomalias: List[ContratoAnomaloIncompleto]) -> None:
        """Incrementa los contadores de estadística_campos_faltantes."""
        campos_a_incrementar: Dict[str, int] = {}
        for anomalia in anomalias:
            if anomalia.motivo == "CAMPO_FALTANTE":
                campos_a_incrementar[anomalia.campo_afectado] = \
                    campos_a_incrementar.get(anomalia.campo_afectado, 0) + 1

        for campo, cantidad in campos_a_incrementar.items():
            for _ in range(cantidad):
                self.repo.increment_campo_faltante(campo)

        if campos_a_incrementar:
            self.session.commit()
