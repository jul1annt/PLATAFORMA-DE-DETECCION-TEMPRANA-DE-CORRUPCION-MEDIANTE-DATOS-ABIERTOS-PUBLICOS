from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Tuple, Optional

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
        limit: int = 50
    ) -> Tuple[List[ContratoProcesado], int]:
        q = self.session.query(ContratoProcesado)

        if filters.entidad:
            q = q.filter(ContratoProcesado.entidad_normalizada.ilike(f"%{filters.entidad}%"))
        if filters.proveedor:
            q = q.filter(ContratoProcesado.proveedor_normalizado.ilike(f"%{filters.proveedor}%"))
        if filters.tipo_contrato:
            q = q.filter(ContratoProcesado.tipo_contrato_normalizado.ilike(f"%{filters.tipo_contrato}%"))
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

        total = q.count()
        items = q.order_by(ContratoProcesado.fecha_publicacion_normalizada.desc()).offset(skip).limit(limit).all()
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
        if filters.motivo:
            q = q.filter(ContratoAnomaloIncompleto.motivo == filters.motivo.upper())
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
