from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal
import logging

from app.modules.procesamiento.models import CalidadDatos, ContratoProcesado

logger = logging.getLogger(__name__)

def validate_quality(db: Session, contrato: ContratoProcesado) -> str:
    """
    Validates a processed contract and registers problems if any.
    Returns the overall state: 'OK', 'INCOMPLETO', 'SOSPECHOSO'.
    """
    state = "OK"
    issues = []

    # 1. Missing fields (INCOMPLETO)
    required_fields = ['id_proceso', 'entidad', 'proveedor', 'valor', 'fecha']
    for field in required_fields:
        if getattr(contrato, field) is None or getattr(contrato, field) == "":
            issues.append({
                "tipo_problema": "INCOMPLETO",
                "campo": field,
                "descripcion": f"El campo {field} está vacío o es nulo."
            })
            if state == "OK":
                state = "INCOMPLETO"

    # 2. Suspicious data (SOSPECHOSO)
    if contrato.valor is not None:
        try:
            val = Decimal(contrato.valor)
            if val < 0:
                issues.append({
                    "tipo_problema": "SOSPECHOSO",
                    "campo": "valor",
                    "descripcion": "El valor del contrato es negativo."
                })
                state = "SOSPECHOSO"
        except Exception:
            pass

    if contrato.fecha is not None:
        try:
            if isinstance(contrato.fecha, date) and contrato.fecha > date.today():
                issues.append({
                    "tipo_problema": "SOSPECHOSO",
                    "campo": "fecha",
                    "descripcion": "La fecha del contrato está en el futuro."
                })
                state = "SOSPECHOSO"
        except Exception:
            pass

    # Save issues if any
    for issue in issues:
        calidad_record = CalidadDatos(
            contrato_id=contrato.id,
            tipo_problema=issue["tipo_problema"],
            campo=issue["campo"],
            descripcion=issue["descripcion"]
        )
        db.add(calidad_record)

    return state
