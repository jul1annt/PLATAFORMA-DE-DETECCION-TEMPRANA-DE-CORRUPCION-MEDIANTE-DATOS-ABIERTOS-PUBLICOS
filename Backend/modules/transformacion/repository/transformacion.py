from sqlalchemy.orm import Session
from datetime import datetime, timezone

from sqlalchemy import case, func, or_, text
from typing import List, Tuple, Optional, Dict
from modules.transformacion.model.ContratoProcesado import ContratoProcesado
from modules.transformacion.model.ContratoAnomaloIncompleto import ContratoAnomaloIncompleto
from modules.transformacion.model.ContratoAnomaliaHistorial import ContratoAnomaliaHistorial
from modules.transformacion.model.EstadisticaCamposFaltantes import EstadisticaCamposFaltantes
from modules.transformacion.model.ProcesamientoLog import ProcesamientoLog
from modules.ingesta.model.RawSecop import RawSecop
from modules.transformacion.domain.filters import ContratoProcesadoFilter, AnomaliaFilter
from modules.transformacion.domain.anomaly import AnomalyFinding


def _clasificar_confianza(promedio: float | None) -> str:
    if promedio is None:
        return "SIN_DATOS"
    if promedio >= 80:
        return "EXCELENTE"
    if promedio >= 60:
        return "ACEPTABLE"
    return "BAJA"


class TransformacionRepository:
    def __init__(self, session: Session):
        self.session = session

    def configure_incremental_query_memory(self) -> None:
        """Limit extra memory to the transaction comparing raw/processed rows."""
        if self.session.get_bind().dialect.name == "postgresql":
            self.session.execute(text("SELECT set_config('work_mem', '32MB', true)"))

    def obtener_ultimo_log_trabajo(self, job_id: int) -> Optional[ProcesamientoLog]:
        return self.session.query(ProcesamientoLog).filter(
            ProcesamientoLog.universo["background_job_id"].as_integer() == job_id,
        ).order_by(ProcesamientoLog.id.desc()).first()

    @staticmethod
    def _criterio_campo_faltante():
        return func.coalesce(
            ContratoAnomaloIncompleto.tipo_anomalia,
            ContratoAnomaloIncompleto.motivo,
        ) == "CAMPO_FALTANTE"

    def obtener_universo_reprocesamiento(self, forzar_reproceso: bool) -> dict:
        max_raw_id = self.session.query(func.max(RawSecop.id)).scalar() or 0
        q = self.session.query(RawSecop.id).filter(RawSecop.id <= max_raw_id)
        if not forzar_reproceso:
            self.configure_incremental_query_memory()
            q = q.outerjoin(
                ContratoProcesado,
                RawSecop.id == ContratoProcesado.raw_secop_id,
            ).filter(or_(
                ContratoProcesado.id.is_(None),
                RawSecop.sincronizado_en > ContratoProcesado.procesado_en,
            ))
        return {
            "max_raw_secop_id": int(max_raw_id),
            "total_candidatos": int(q.count()),
            "forzar_reproceso": bool(forzar_reproceso),
        }

    # ─── ContratoProcesado ─────────────────────────────────────────────

    def save_all_contratos(self, contratos: List[ContratoProcesado]) -> None:
        self.session.add_all(contratos)
        self.session.flush()

    def get_contrato_by_id(self, id: int) -> Optional[ContratoProcesado]:
        return self.session.query(ContratoProcesado).filter(ContratoProcesado.id == id).first()

    def find_by_raw_secop_id(self, raw_secop_id: int) -> Optional[ContratoProcesado]:
        return self.session.query(ContratoProcesado).filter(
            ContratoProcesado.raw_secop_id == raw_secop_id
        ).first()

    def obtener_contratos_por_raw_ids(
        self, raw_secop_ids: list[int]
    ) -> dict[int, ContratoProcesado]:
        """Cargue contratos existentes para un lote sin una consulta por fila cruda."""
        if not raw_secop_ids:
            return {}
        contratos = self.session.query(ContratoProcesado).filter(
            ContratoProcesado.raw_secop_id.in_(raw_secop_ids)
        ).all()
        return {contrato.raw_secop_id: contrato for contrato in contratos}

    def find_by_hash(self, normalized_hash: str) -> Optional[ContratoProcesado]:
        return self.session.query(ContratoProcesado).filter(
            ContratoProcesado.normalized_hash == normalized_hash
        ).first()

    def search_contratos(
        self,
        filters: ContratoProcesadoFilter,
        skip: int = 0,
        limit: int = 50,
        sort: Optional[str] = None,
        order: str = "desc"
    ) -> Tuple[List[ContratoProcesado], int]:
        q = self.session.query(ContratoProcesado)

        if filters.entidad:
            q = q.filter(ContratoProcesado.entidad_normalizada.ilike(f"%{filters.entidad}%"))
        if filters.proveedor:
            q = q.filter(ContratoProcesado.proveedor_normalizado.ilike(f"%{filters.proveedor}%"))
        if filters.modalidad:
            q = q.filter(ContratoProcesado.modalidad_contratacion.ilike(f"%{filters.modalidad}%"))
        if filters.estado:
            q = q.filter(ContratoProcesado.estado_normalizado.ilike(f"%{filters.estado}%"))
        if filters.fecha_inicio:
            q = q.filter(ContratoProcesado.fecha_publicacion_normalizada >= filters.fecha_inicio)
        if filters.fecha_fin:
            q = q.filter(ContratoProcesado.fecha_publicacion_normalizada <= filters.fecha_fin)
        if filters.valor_min is not None:
            q = q.filter(ContratoProcesado.valor_total_normalizado >= filters.valor_min)
        if filters.valor_max is not None:
            q = q.filter(ContratoProcesado.valor_total_normalizado <= filters.valor_max)
        if filters.solo_incompletos:
            q = q.filter(ContratoProcesado.es_incompleto == True)
        if getattr(filters, 'solo_sospechosos', False):
            q = q.filter(ContratoProcesado.es_sospechoso == True)
        if filters.nivel_confianza_min is not None:
            q = q.filter(ContratoProcesado.nivel_confianza >= filters.nivel_confianza_min)
        if filters.nivel_confianza_max is not None:
            q = q.filter(ContratoProcesado.nivel_confianza <= filters.nivel_confianza_max)
        if filters.query:
            pattern = f"%{filters.query}%"
            q = q.filter(or_(
                ContratoProcesado.entidad_normalizada.ilike(pattern),
                ContratoProcesado.proveedor_normalizado.ilike(pattern),
                ContratoProcesado.nit_proveedor.ilike(pattern),
                ContratoProcesado.id_del_proceso.ilike(pattern),
            ))
        if filters.solo_alto_riesgo:
            q = q.filter(ContratoProcesado.clasificacion_riesgo == "ALTO")

        total = q.count()
        
        sort_field = ContratoProcesado.fecha_publicacion_normalizada
        if sort:
            if sort == "valor" or sort == "valor_total_normalizado":
                sort_field = ContratoProcesado.valor_total_normalizado
            elif sort == "precio_base_normalizado":
                sort_field = ContratoProcesado.precio_base_normalizado
            elif sort == "fecha":
                sort_field = ContratoProcesado.fecha_publicacion_normalizada
            elif sort == "id":
                sort_field = ContratoProcesado.id
            elif sort == "entidad":
                sort_field = ContratoProcesado.entidad_normalizada
            elif sort == "proveedor":
                sort_field = ContratoProcesado.proveedor_normalizado
            elif sort == "riesgo":
                sort_field = ContratoProcesado.nivel_confianza

        if order == "asc":
            q = q.order_by(sort_field.asc())
        else:
            q = q.order_by(sort_field.desc())

        items = q.offset(skip).limit(limit).all()
        return items, total

    # ─── ContratoAnomaloIncompleto ─────────────────────────────────────

    @staticmethod
    def _materializar_anomalia(
        hallazgo: AnomalyFinding,
        contrato_id: int | None = None,
    ) -> ContratoAnomaloIncompleto:
        return ContratoAnomaloIncompleto(
            raw_secop_id=hallazgo.raw_secop_id,
            id_contrato_procesado=contrato_id,
            motivo=hallazgo.motivo,
            valor_detectado=hallazgo.valor_detectado,
            tipo_anomalia=hallazgo.tipo_anomalia,
            valor_original=hallazgo.valor_original,
            descripcion=hallazgo.descripcion,
            campo_afectado=hallazgo.campo_afectado,
        )

    def save_all_anomalias(
        self,
        anomalias: List[AnomalyFinding],
        *,
        contrato_id: int | None = None,
    ) -> None:
        self.session.add_all([
            self._materializar_anomalia(item, contrato_id)
            for item in anomalias
        ])
        self.session.flush()

    def replace_anomalias(
        self,
        contrato_id: int,
        anomalias: List[AnomalyFinding],
        *,
        raw_secop_id: int,
    ) -> None:
        self.replace_anomalias_batch([(contrato_id, raw_secop_id, anomalias)])

    def replace_anomalias_batch(
        self,
        reemplazos: List[Tuple[int, int, List[AnomalyFinding]]],
        *,
        nuevos_raw_ids: set[int] | None = None,
    ) -> None:
        """Reconcile current findings for many contracts in one read/write batch."""
        if not reemplazos:
            return

        # A contract inserted in this transaction cannot have current findings.
        # Skip those IDs in the lookup during large initial loads.
        nuevos_raw_ids = nuevos_raw_ids or set()
        raw_ids = [
            raw_secop_id for _contrato_id, raw_secop_id, _ in reemplazos
            if raw_secop_id not in nuevos_raw_ids
        ]
        existentes = (
            self.session.query(ContratoAnomaloIncompleto).filter(
                ContratoAnomaloIncompleto.raw_secop_id.in_(raw_ids)
            ).all()
            if raw_ids else []
        )
        existentes_por_raw: dict[int, list[ContratoAnomaloIncompleto]] = {}
        for existente in existentes:
            existentes_por_raw.setdefault(existente.raw_secop_id, []).append(existente)

        nuevas: list[ContratoAnomaloIncompleto] = []
        retiradas: list[ContratoAnomaloIncompleto] = []
        for contrato_id, raw_secop_id, anomalias in reemplazos:
            por_clave: dict[tuple, list[ContratoAnomaloIncompleto]] = {}
            for existente in existentes_por_raw.get(raw_secop_id, []):
                clave = self._clave_anomalia(existente)
                por_clave.setdefault(clave, []).append(existente)

            for hallazgo in anomalias:
                clave = self._clave_anomalia(hallazgo)
                candidatas = por_clave.pop(clave, [])
                firma = self._contenido_anomalia(hallazgo)
                sin_cambios = next(
                    (item for item in candidatas if self._contenido_anomalia(item) == firma),
                    None,
                )
                if sin_cambios:
                    if sin_cambios.id_contrato_procesado != contrato_id:
                        sin_cambios.id_contrato_procesado = contrato_id
                    retiradas.extend(item for item in candidatas if item is not sin_cambios)
                else:
                    retiradas.extend(candidatas)
                    nuevas.append(self._materializar_anomalia(hallazgo, contrato_id))

            retiradas.extend(item for grupo in por_clave.values() for item in grupo)

        ahora = datetime.now(timezone.utc)
        for retirada in retiradas:
            self.session.add(ContratoAnomaliaHistorial(
                anomalia_id_original=retirada.id,
                raw_secop_id=retirada.raw_secop_id,
                id_contrato_procesado=retirada.id_contrato_procesado,
                motivo=retirada.motivo,
                valor_detectado=retirada.valor_detectado,
                tipo_anomalia=retirada.tipo_anomalia,
                valor_original=retirada.valor_original,
                descripcion=retirada.descripcion,
                campo_afectado=retirada.campo_afectado,
                fecha_inicio=retirada.created_at,
                fecha_fin=ahora,
            ))
            self.session.delete(retirada)

        # Free the unique (raw, type, field) key before inserting its updated
        # replacement. PostgreSQL can otherwise flush INSERTs before DELETEs
        # and reject a valid replacement against uq_cai_raw_tipo_campo.
        if retiradas:
            self.session.flush()

        self.session.add_all(nuevas)
        self.session.flush()

    @staticmethod
    def _clave_anomalia(anomalia) -> tuple:
        return (
            anomalia.raw_secop_id,
            anomalia.tipo_anomalia or anomalia.motivo,
            anomalia.campo_afectado,
        )

    @staticmethod
    def _contenido_anomalia(anomalia) -> tuple:
        return (
            anomalia.motivo,
            anomalia.valor_detectado,
            anomalia.tipo_anomalia or anomalia.motivo,
            anomalia.valor_original,
            anomalia.descripcion,
            anomalia.campo_afectado,
        )

    def search_anomalias(
        self,
        filters: AnomaliaFilter,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[ContratoAnomaloIncompleto], int]:
        q = self.session.query(ContratoAnomaloIncompleto)

        if filters.raw_secop_id:
            q = q.filter(ContratoAnomaloIncompleto.raw_secop_id == filters.raw_secop_id)
        if filters.id_contrato_procesado:
            q = q.filter(ContratoAnomaloIncompleto.id_contrato_procesado == filters.id_contrato_procesado)
        if filters.motivo:
            q = q.filter(ContratoAnomaloIncompleto.motivo == filters.motivo.upper())
        if filters.tipo_anomalia:
            q = q.filter(ContratoAnomaloIncompleto.tipo_anomalia == filters.tipo_anomalia.upper())
        if filters.campo_afectado:
            q = q.filter(ContratoAnomaloIncompleto.campo_afectado == filters.campo_afectado)

        total = q.count()
        items = q.order_by(ContratoAnomaloIncompleto.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    # ─── EstadisticaCamposFaltantes ────────────────────────────────────

    def increment_campo_faltante(self, nombre_campo: str) -> None:
        """
        Incrementa en +1 el contador del campo faltante.
        Si no existe el registro, lo crea automáticamente.
        """
        registro = self.session.query(EstadisticaCamposFaltantes).filter(
            EstadisticaCamposFaltantes.nombre_campo == nombre_campo
        ).first()

        if registro:
            registro.contador_faltantes += 1
        else:
            registro = EstadisticaCamposFaltantes(
                nombre_campo=nombre_campo,
                contador_faltantes=1
            )
            self.session.add(registro)
        # No commit aquí — se hace en batch al final del proceso

    def get_all_estadisticas(self) -> List[EstadisticaCamposFaltantes]:
        return self.session.query(EstadisticaCamposFaltantes)\
            .order_by(EstadisticaCamposFaltantes.contador_faltantes.desc())\
            .all()

    def get_metricas_calidad(self) -> Dict[str, float | int | str | None]:
        total_contratos, incompletos, sospechosos, _alto, promedio_confianza = (
            self._agregar_metricas_contratos()
        )
        completos = total_contratos - incompletos
        porcentaje_incompletos = round(incompletos / total_contratos * 100, 2) if total_contratos else None
        porcentaje_completos = round(completos / total_contratos * 100, 2) if total_contratos else None
        porcentaje_sospechosos = round(sospechosos / total_contratos * 100, 2) if total_contratos else None

        return {
            "total_contratos": total_contratos,
            "completos": completos,
            "incompletos": incompletos,
            "sospechosos": sospechosos,
            "porcentaje_completos": porcentaje_completos,
            "porcentaje_incompletos": porcentaje_incompletos,
            "porcentaje_sospechosos": porcentaje_sospechosos,
            "promedio_confianza": promedio_confianza,
            "calificacion_confianza": _clasificar_confianza(promedio_confianza),
        }

    def get_dashboard_metricas(self) -> Dict[str, float | int | str | None]:
        total, incompletos, sospechosos, alto, promedio = self._agregar_metricas_contratos()
        completos = total - incompletos
        porcentaje_completos = round(completos / total * 100, 2) if total else None
        porcentaje_incompletos = round(incompletos / total * 100, 2) if total else None
        porcentaje_sospechosos = round(sospechosos / total * 100, 2) if total else None
        return {
            "total_contratos": total,
            "total_completos": completos,
            "pct_incompletos": porcentaje_incompletos,
            "pct_sospechosos": porcentaje_sospechosos,
            "pct_alto_riesgo": round(alto / total * 100, 2) if total else None,
            "total_incompletos": incompletos,
            "total_sospechosos": sospechosos,
            "total_alto_riesgo": alto,
            "promedio_confianza": promedio,
            "calificacion_confianza": _clasificar_confianza(promedio),
            "estado_datos": "DISPONIBLE" if total else "SIN_DATOS",
        }

    def _agregar_metricas_contratos(self) -> tuple[int, int, int, int, float | None]:
        row = self.session.query(
            func.count(ContratoProcesado.id),
            func.count(case((ContratoProcesado.es_incompleto.is_(True), 1))),
            func.count(case((ContratoProcesado.es_sospechoso.is_(True), 1))),
            func.count(case((ContratoProcesado.clasificacion_riesgo == "ALTO", 1))),
            func.avg(ContratoProcesado.nivel_confianza),
        ).one()
        total, incompletos, sospechosos, alto, promedio = row
        total = int(total or 0)
        return (
            total,
            int(incompletos or 0),
            int(sospechosos or 0),
            int(alto or 0),
            round(float(promedio), 2) if total and promedio is not None else None,
        )

    def get_risk_distribution(self) -> list[dict]:
        colors = {
            "ALTO": "#ef4444", "MEDIO": "#f59e0b",
            "BAJO": "#10b981", "SIN_EVALUAR": "#94a3b8",
        }
        labels = {
            "ALTO": "Alto Riesgo", "MEDIO": "Riesgo Medio",
            "BAJO": "Riesgo Bajo", "SIN_EVALUAR": "Sin evaluar",
        }
        rows = self.session.query(
            ContratoProcesado.clasificacion_riesgo,
            func.count(ContratoProcesado.id),
        ).group_by(ContratoProcesado.clasificacion_riesgo).all()
        return [
            {"name": labels.get(level or "SIN_EVALUAR", "Sin evaluar"),
             "value": count, "color": colors.get(level or "SIN_EVALUAR", "#94a3b8")}
            for level, count in rows if count
        ]

    def get_anomaly_distribution(self) -> list[dict]:
        incompletos, sospechosos, alto = self.session.query(
            func.count(case((ContratoProcesado.es_incompleto.is_(True), 1))),
            func.count(case((ContratoProcesado.es_sospechoso.is_(True), 1))),
            func.count(case((ContratoProcesado.clasificacion_riesgo == "ALTO", 1))),
        ).one()
        counts = {
            "Incompletos": incompletos or 0,
            "Sospechosos": sospechosos or 0,
            "Alto Riesgo": alto or 0,
        }
        colors = {"Incompletos": "#f59e0b", "Sospechosos": "#8b5cf6", "Alto Riesgo": "#ec4899"}
        return [{"name": key, "value": value, "color": colors[key]} for key, value in counts.items() if value]

    def get_top_providers(self, limit: int) -> list[dict]:
        nit_identidad = ContratoProcesado.nit_proveedor_clave
        rows = self.session.query(
            nit_identidad,
            func.max(ContratoProcesado.proveedor_normalizado),
            func.count(ContratoProcesado.id),
        ).filter(
            nit_identidad.is_not(None),
        ).group_by(nit_identidad).order_by(
            func.count(ContratoProcesado.id).desc()
        ).limit(limit).all()
        return [{"nit": nit, "name": name or nit, "contracts": count} for nit, name, count in rows]

    def autocomplete(self, query: str, limit: int) -> list[dict]:
        pattern = f"%{query}%"
        entidades = self.session.query(ContratoProcesado.entidad_normalizada).filter(
            ContratoProcesado.entidad_normalizada.ilike(pattern)
        ).distinct().limit(limit).all()
        proveedores = self.session.query(ContratoProcesado.proveedor_normalizado).filter(
            ContratoProcesado.proveedor_normalizado.ilike(pattern)
        ).distinct().limit(limit).all()
        results = ([{"text": row[0], "type": "ENTIDAD"} for row in entidades]
                   + [{"text": row[0], "type": "PROVEEDOR"} for row in proveedores])
        return results[:limit]

    def recalculate_porcentajes_estadisticas_campos(self) -> None:
        total_contratos = self.session.query(ContratoProcesado.id).count()
        self.session.query(EstadisticaCamposFaltantes).delete(synchronize_session=False)
        conteos = self.session.query(
            ContratoAnomaloIncompleto.campo_afectado,
            func.count(ContratoAnomaloIncompleto.id),
        ).filter(self._criterio_campo_faltante()).group_by(
            ContratoAnomaloIncompleto.campo_afectado
        ).all()
        for campo, cantidad in conteos:
            porcentaje = (cantidad / total_contratos * 100) if total_contratos else 0
            self.session.add(EstadisticaCamposFaltantes(
                nombre_campo=campo,
                contador_faltantes=cantidad,
                porcentaje_total=round(porcentaje, 2),
            ))
        self.session.flush()

    # ─── ProcesamientoLog ─────────────────────────────────────────────
    
    def search_logs(self, skip: int = 0, limit: int = 50) -> Tuple[List[ProcesamientoLog], int]:
        q = self.session.query(ProcesamientoLog)
        total = q.count()
        items = q.order_by(ProcesamientoLog.created_at.desc()).offset(skip).limit(limit).all()
        return items, total
