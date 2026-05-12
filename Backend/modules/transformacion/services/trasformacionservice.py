import logging
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Dict, Any

from modules.transformacion.services.normalization_service import (
    normalize_date, normalize_amount, normalize_text, generate_hash
)
from modules.transformacion.model.ContratoProcesado import ContratoProcesado
from modules.transformacion.repository.transformacion import TransformacionRepository
from modules.ingesta.model.RawSecop import RawSecop

logger = logging.getLogger(__name__)

class TransformacionService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = TransformacionRepository(session)

    def process_raw_data(self, limite: int = 1000, forzar_reproceso: bool = False) -> Dict[str, int]:
        """
        Process raw data from RawSecop and create ContratoProcesado records.
        """
        query = self.session.query(RawSecop)
        
        if not forzar_reproceso:
            # Simplest approach to not re-process: Left outer join or subquery.
            # For performance, we can get raw_data_id that have not been processed.
            subquery = self.session.query(ContratoProcesado.raw_data_id).subquery()
            query = query.filter(~RawSecop.id.in_(subquery))
            
        raw_records = query.limit(limite).all()
        
        processed_count = 0
        skipped_count = 0
        
        nuevos_contratos = []
        
        for raw in raw_records:
            # 1. Normalize data
            normalized_data = {
                "raw_data_id": raw.id,
                "id_proceso": normalize_text(raw.id_del_proceso),
                "entidad": normalize_text(raw.entidad),
                "proveedor": normalize_text(raw.nombre_del_proveedor),
                "valor_contrato": normalize_amount(raw.valor_total_adjudicacion) if raw.valor_total_adjudicacion else normalize_amount(raw.precio_base),
                "fecha_contrato": normalize_date(raw.fecha_adjudicacion) if raw.fecha_adjudicacion else normalize_date(raw.fecha_de_publicacion_del),
                "tipo_contrato": normalize_text(raw.tipo_de_contrato),
                "estado": normalize_text(raw.estado_del_procedimiento)
            }
            
            # 2. Generate hash
            data_hash = generate_hash(normalized_data)
            normalized_data["normalized_hash"] = data_hash
            
            # 3. Check for existing hash if forcing reprocessing
            if forzar_reproceso:
                existing = self.repo.find_by_hash(data_hash)
                if existing:
                    skipped_count += 1
                    continue
                    
            # 4. Create entity
            nuevo_contrato = ContratoProcesado(**normalized_data)
            nuevos_contratos.append(nuevo_contrato)
            processed_count += 1
            
            # Batch insert every 500
            if len(nuevos_contratos) >= 500:
                self.repo.save_all(nuevos_contratos)
                nuevos_contratos = []

        # Insert remaining
        if nuevos_contratos:
            self.repo.save_all(nuevos_contratos)
            
        return {
            "procesados": processed_count,
            "omitidos": skipped_count,
            "total_evaluados": len(raw_records)
        }
