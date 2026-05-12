from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from typing import List, Tuple, Optional
from modules.transformacion.model.ContratoProcesado import ContratoProcesado
from modules.transformacion.dto.request import ContratoProcesadoFilterDTO

class TransformacionRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, contrato: ContratoProcesado) -> ContratoProcesado:
        self.session.add(contrato)
        self.session.commit()
        self.session.refresh(contrato)
        return contrato

    def save_all(self, contratos: List[ContratoProcesado]) -> None:
        self.session.add_all(contratos)
        self.session.commit()

    def get_by_id(self, id: int) -> Optional[ContratoProcesado]:
        return self.session.query(ContratoProcesado).filter(ContratoProcesado.id == id).first()

    def find_by_raw_data_id(self, raw_data_id: int) -> Optional[ContratoProcesado]:
        return self.session.query(ContratoProcesado).filter(ContratoProcesado.raw_data_id == raw_data_id).first()
        
    def find_by_hash(self, normalized_hash: str) -> Optional[ContratoProcesado]:
        return self.session.query(ContratoProcesado).filter(ContratoProcesado.normalized_hash == normalized_hash).first()

    def search(self, filters: ContratoProcesadoFilterDTO, skip: int = 0, limit: int = 100) -> Tuple[List[ContratoProcesado], int]:
        query = self.session.query(ContratoProcesado)

        if filters.entidad:
            query = query.filter(ContratoProcesado.entidad.ilike(f"%{filters.entidad}%"))
        if filters.proveedor:
            query = query.filter(ContratoProcesado.proveedor.ilike(f"%{filters.proveedor}%"))
        if filters.tipo_contrato:
            query = query.filter(ContratoProcesado.tipo_contrato.ilike(f"%{filters.tipo_contrato}%"))
        
        if filters.fecha_inicio:
            query = query.filter(ContratoProcesado.fecha_contrato >= filters.fecha_inicio)
        if filters.fecha_fin:
            query = query.filter(ContratoProcesado.fecha_contrato <= filters.fecha_fin)
            
        if filters.valor_min is not None:
            query = query.filter(ContratoProcesado.valor_contrato >= filters.valor_min)
        if filters.valor_max is not None:
            query = query.filter(ContratoProcesado.valor_contrato <= filters.valor_max)

        total = query.count()
        items = query.order_by(ContratoProcesado.fecha_contrato.desc()).offset(skip).limit(limit).all()

        return items, total
