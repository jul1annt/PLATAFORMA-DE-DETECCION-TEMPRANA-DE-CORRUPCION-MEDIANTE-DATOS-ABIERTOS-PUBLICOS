import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from uuid import UUID

from app.modules.ingestion.models import DatoCrudo
from app.modules.fuentes.models import FuenteDatos
from app.modules.logs.models import LogSincronizacion
from app.connectors.mock import MockConnector

def get_connector(tipo: str):
    if tipo.lower() == "mock" or tipo.lower() == "secop_mock":
        return MockConnector()
    return None

def hash_record(record: dict) -> str:
    record_string = json.dumps(record, sort_keys=True)
    return hashlib.sha256(record_string.encode('utf-8')).hexdigest()

def run_ingestion_for_source(db: Session, fuente: FuenteDatos):
    log = LogSincronizacion(fuente_id=fuente.id, estado="in_progress")
    db.add(log)
    db.commit()
    db.refresh(log)

    try:
        connector = get_connector(fuente.tipo)
        if not connector:
            raise ValueError(f"Connector not found for type: {fuente.tipo}")
        
        records = connector.fetch_data(fuente.endpoint)
        
        new_records_count = 0
        for record in records:
            record_hash = hash_record(record)
            existing = db.query(DatoCrudo).filter(DatoCrudo.hash_registro == record_hash).first()
            
            if not existing:
                dato_crudo = DatoCrudo(
                    fuente_id=fuente.id,
                    hash_registro=record_hash,
                    datos_json=record
                )
                db.add(dato_crudo)
                new_records_count += 1
        
        fuente.ultima_sincronizacion = datetime.now(timezone.utc)
        
        log.estado = "success"
        log.cantidad_registros = new_records_count
        log.mensaje = f"Successfully synced {new_records_count} new records out of {len(records)} fetched."
        
        db.commit()
        return log

    except Exception as e:
        db.rollback()
        log.estado = "failed"
        log.mensaje = str(e)
        db.commit()
        return log

def run_scheduled_ingestion(db: Session):
    active_sources = db.query(FuenteDatos).filter(FuenteDatos.estado == 'activa').all()
    now = datetime.now(timezone.utc)
    
    for fuente in active_sources:
        if not fuente.ultima_sincronizacion:
            run_ingestion_for_source(db, fuente)
        else:
            days_since_last_sync = (now - fuente.ultima_sincronizacion).days
            if days_since_last_sync >= fuente.frecuencia_dias:
                run_ingestion_for_source(db, fuente)
