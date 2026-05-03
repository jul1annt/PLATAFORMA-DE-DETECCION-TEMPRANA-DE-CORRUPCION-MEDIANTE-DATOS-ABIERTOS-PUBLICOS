from sqlalchemy.orm import Session
from app.modules.procesamiento.models import CambiosContratos, ContratoProcesado

def detect_and_record_changes(db: Session, existing: ContratoProcesado, new_data: dict):
    """
    Compares the existing contract with normalized new_data.
    Registers changes in cambios_contratos and updates the existing record.
    Returns True if changes were found and applied.
    """
    fields_to_check = ['entidad', 'proveedor', 'valor', 'fecha', 'tipo_contrato']
    changes_detected = False

    for field in fields_to_check:
        old_val = getattr(existing, field)
        new_val = new_data.get(field)

        # Convert to string for easy comparison and storage, treating None as empty string
        old_str = str(old_val) if old_val is not None else ""
        new_str = str(new_val) if new_val is not None else ""

        if old_str != new_str:
            # Register change
            cambio = CambiosContratos(
                id_proceso=existing.id_proceso,
                campo=field,
                valor_anterior=old_str,
                valor_nuevo=new_str
            )
            db.add(cambio)
            
            # Update the existing record
            setattr(existing, field, new_val)
            changes_detected = True

    return changes_detected
