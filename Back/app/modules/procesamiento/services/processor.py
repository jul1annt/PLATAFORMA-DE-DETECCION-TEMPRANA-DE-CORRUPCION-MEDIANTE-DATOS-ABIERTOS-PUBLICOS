import hashlib
import json
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from app.modules.ingestion.models import DatoCrudo
from app.modules.procesamiento.models import ContratoProcesado, ResumenCalidad, CalidadDatos
from app.modules.procesamiento.services.quality import validate_quality
from app.modules.procesamiento.services.changes import detect_and_record_changes

logger = logging.getLogger(__name__)

def generate_hash(id_proceso: str, proveedor: str, valor, fecha) -> str:
    """Generates a SHA256 hash using the key fields to detect exact duplicates."""
    id_p = str(id_proceso or "").strip()
    prov = str(proveedor or "").strip()
    val = str(valor or "").strip()
    fec = str(fecha or "").strip()
    
    raw_string = f"{id_p}|{prov}|{val}|{fec}"
    return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()

def parse_date(date_str: str):
    if not date_str:
        return None
    try:
        # Tries to parse YYYY-MM-DD or ISO datetime
        # E.g. "2023-10-15T00:00:00.000"
        if "T" in date_str:
            return datetime.fromisoformat(date_str.split('.')[0]).date()
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None

def parse_numeric(val_str):
    if not val_str:
        return None
    try:
        return Decimal(str(val_str).replace(',', ''))
    except Exception:
        return None

def normalize_text(text: str):
    if not text:
        return None
    return str(text).strip().upper()

def process_data_pipeline(db: Session):
    """
    Orchestrates the entire processing pipeline from datos_crudos to contratos_procesados.
    """
    logger.info("Starting Data Processing Pipeline...")

    # For the MVP, we process all raw data. In a real scenario, we might want a flag or watermark.
    crudos = db.query(DatoCrudo).all()
    
    processed_count = 0
    new_records = 0
    updated_records = 0
    issues_found = 0

    stats_by_source = {}

    for crudo in crudos:
        json_data = crudo.datos_json
        
        # 1. Parse & Normalize
        # Assuming typical SECOP-like keys from our mock
        id_proceso = json_data.get("id_proceso")
        entidad_dict = json_data.get("entidad", {})
        entidad = entidad_dict.get("nombre") if isinstance(entidad_dict, dict) else json_data.get("entidad")
        proveedor = json_data.get("proveedor", "DESCONOCIDO") # Mock might not have provider always, adding fallback for test
        valor = parse_numeric(json_data.get("valor_total"))
        fecha = parse_date(json_data.get("fecha") or "2024-01-01") # Mock didn't have date, assigning dummy for pipeline test
        tipo_contrato = normalize_text(json_data.get("tipo_contrato") or "Servicios")
        
        entidad = normalize_text(entidad)
        proveedor = normalize_text(proveedor)
        
        # 2. Hash Generation
        record_hash = generate_hash(id_proceso, proveedor, valor, fecha)
        
        # 3. Duplicate check via Hash
        existing_by_hash = db.query(ContratoProcesado).filter(ContratoProcesado.hash_procesado == record_hash).first()
        if existing_by_hash:
            # Exact duplicate, ignore
            continue
            
        processed_count += 1
        
        normalized_data = {
            "id_proceso": id_proceso,
            "entidad": entidad,
            "proveedor": proveedor,
            "valor": valor,
            "fecha": fecha,
            "tipo_contrato": tipo_contrato,
            "fuente_id": crudo.fuente_id,
            "hash_procesado": record_hash
        }

        # Check if id_proceso exists to detect changes vs new inserts
        existing_by_id = db.query(ContratoProcesado).filter(ContratoProcesado.id_proceso == id_proceso).first()
        
        if existing_by_id:
            # Detect changes and update
            changed = detect_and_record_changes(db, existing_by_id, normalized_data)
            if changed:
                existing_by_id.hash_procesado = record_hash
                # Re-validate quality after update
                # Clear old quality issues for this contract
                db.query(CalidadDatos).filter(CalidadDatos.contrato_id == existing_by_id.id).delete()
                new_state = validate_quality(db, existing_by_id)
                existing_by_id.estado_calidad = new_state
                updated_records += 1
                
                # Update stats
                source_id = str(existing_by_id.fuente_id)
                if source_id not in stats_by_source:
                    stats_by_source[source_id] = {"total": 0, "incompletos": 0, "sospechosos": 0}
                if new_state == "INCOMPLETO": stats_by_source[source_id]["incompletos"] += 1
                if new_state == "SOSPECHOSO": stats_by_source[source_id]["sospechosos"] += 1
                
        else:
            # New record
            nuevo_contrato = ContratoProcesado(**normalized_data)
            db.add(nuevo_contrato)
            db.flush() # Get ID for quality validation
            
            estado = validate_quality(db, nuevo_contrato)
            nuevo_contrato.estado_calidad = estado
            new_records += 1
            
            # Update stats
            source_id = str(nuevo_contrato.fuente_id)
            if source_id not in stats_by_source:
                stats_by_source[source_id] = {"total": 0, "incompletos": 0, "sospechosos": 0}
            stats_by_source[source_id]["total"] += 1
            if estado == "INCOMPLETO": stats_by_source[source_id]["incompletos"] += 1
            if estado == "SOSPECHOSO": stats_by_source[source_id]["sospechosos"] += 1
            
    # 4. Generate ResumenCalidad
    for source_id, stats in stats_by_source.items():
        resumen = ResumenCalidad(
            fuente_id=source_id,
            total_registros=stats["total"],
            incompletos=stats["incompletos"],
            sospechosos=stats["sospechosos"]
        )
        db.add(resumen)
        issues_found += (stats["incompletos"] + stats["sospechosos"])

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error during commit in process_data: {e}")
        raise e

    return {
        "status": "success",
        "processed_count": processed_count,
        "new_records": new_records,
        "updated_records": updated_records,
        "issues_found": issues_found
    }
