from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Tuple, Optional, Dict
from sqlalchemy import func

from modules.transformacion.model.ContratoProcesado import ContratoProcesado
from modules.transformacion.model.ContratoAnomaloIncompleto import ContratoAnomaloIncompleto
from modules.transformacion.model.EstadisticaCamposFaltantes import EstadisticaCamposFaltantes
from modules.transformacion.dto.request import ContratoProcesadoFilterDTO, AnomaliaFilterDTO


class TransformacionRepository:
    def __init__(self, session: Session):
        self.session = session

    # ─── ContratoProcesado ─────────────────────────────────────────────

    def save_all_contratos(self, contratos: List[ContratoProcesado]) -> None:
        self.session.add_all(contratos)
        self.session.commit()

    def get_contrato_by_id(self, id: int) -> Optional[ContratoProcesado]:
        return self.session.query(ContratoProcesado).filter(ContratoProcesado.id == id).first()

    def find_by_raw_secop_id(self, raw_secop_id: int) -> Optional[ContratoProcesado]:
        return self.session.query(ContratoProcesado).filter(
            ContratoProcesado.raw_secop_id == raw_secop_id
        ).first()

    def find_by_hash(self, normalized_hash: str) -> Optional[ContratoProcesado]:
        return self.session.query(ContratoProcesado).filter(
            ContratoProcesado.normalized_hash == normalized_hash
        ).first()

    def search_contratos(
        self,
        filters: ContratoProcesadoFilterDTO,
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

    def save_all_anomalias(self, anomalias: List[ContratoAnomaloIncompleto]) -> None:
        self.session.add_all(anomalias)
        self.session.commit()

    def search_anomalias(
        self,
        filters: AnomaliaFilterDTO,
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

    def get_metricas_calidad(self) -> Dict[str, float]:
        total_contratos = self.session.query(ContratoProcesado).count()
        incompletos = self.session.query(ContratoProcesado).filter(ContratoProcesado.es_incompleto == True).count()
        sospechosos = self.session.query(ContratoProcesado).filter(ContratoProcesado.es_sospechoso == True).count()
        
        completos = total_contratos - incompletos
        porcentaje_incompletos = (incompletos / total_contratos * 100) if total_contratos > 0 else 0.0
        porcentaje_completos = (completos / total_contratos * 100) if total_contratos > 0 else 0.0
        porcentaje_sospechosos = (sospechosos / total_contratos * 100) if total_contratos > 0 else 0.0

        # Promedio de nivel_confianza (ignorar NULLs)
        avg_row = self.session.query(func.avg(ContratoProcesado.nivel_confianza)).scalar()
        promedio_confianza = round(float(avg_row), 2) if avg_row is not None else 100.0

        return {
            "total_contratos": total_contratos,
            "completos": completos,
            "incompletos": incompletos,
            "sospechosos": sospechosos,
            "porcentaje_completos": round(porcentaje_completos, 2),
            "porcentaje_incompletos": round(porcentaje_incompletos, 2),
            "porcentaje_sospechosos": round(porcentaje_sospechosos, 2),
            "promedio_confianza": promedio_confianza,
        }

    def recalculate_porcentajes_estadisticas_campos(self) -> None:
        total_contratos = self.session.query(ContratoProcesado).count()
        if total_contratos == 0:
            return
            
        estadisticas = self.session.query(EstadisticaCamposFaltantes).all()
        for est in estadisticas:
            porcentaje = (est.contador_faltantes / total_contratos) * 100
            est.porcentaje_total = round(porcentaje, 2)
        
        # Commit will be handled by the caller or we can flush
        self.session.flush()
