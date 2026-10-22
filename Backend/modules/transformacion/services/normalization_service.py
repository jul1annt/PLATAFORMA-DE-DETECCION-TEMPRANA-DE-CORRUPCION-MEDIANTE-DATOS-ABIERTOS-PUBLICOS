import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Any, Dict, Mapping

from modules.transformacion.domain.anomaly import AnomalyFinding


_IDENTIFICADORES_AUSENTES = {
    "-", "N/A", "N.A.", "NA", "NO APLICA", "NO DEFINIDO",
    "NONE", "NULL", "SIN INFORMACION", "SIN INFORMACIÓN", "SIN REGISTRO", "SIN NIT",
}


def detect_anomalies(
    values: Mapping[str, Any],
    *,
    raw_secop_id: int,
    current_date: date,
) -> list[AnomalyFinding]:
    """Detect current anomalies without writing rows or changing counters."""
    findings: list[AnomalyFinding] = []
    required_fields = (
        "entidad",
        "nombre_del_proveedor",
        "valor_total_adjudicacion",
        "fecha_de_publicacion_del",
        "tipo_de_contrato",
    )
    future_date_fields = (
        "fecha_de_publicacion_del",
        "fecha_adjudicacion",
        "fecha_de_ultima_publicaci",
        "fecha_de_apertura_efectiva",
    )
    amount_fields = ("precio_base", "valor_total_adjudicacion")

    for field in required_fields:
        value = values.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            findings.append(AnomalyFinding(
                raw_secop_id=raw_secop_id,
                motivo="CAMPO_FALTANTE",
                valor_detectado=None,
                tipo_anomalia="CAMPO_FALTANTE",
                valor_original=None,
                descripcion=f"El contrato no contiene {field}",
                campo_afectado=field,
            ))

    for field in future_date_fields:
        value = values.get(field)
        if value is not None:
            parsed = value.date() if isinstance(value, datetime) else value
            if isinstance(parsed, date) and parsed > current_date:
                findings.append(AnomalyFinding(
                    raw_secop_id=raw_secop_id,
                    motivo="FECHA_FUTURA",
                    valor_detectado=str(value),
                    tipo_anomalia="FECHA_FUTURA",
                    valor_original=str(value),
                    descripcion="El contrato contiene una fecha futura inválida",
                    campo_afectado=field,
                ))

    for field in amount_fields:
        value = values.get(field)
        if value is not None:
            try:
                negative = float(value) < 0
            except (TypeError, ValueError, OverflowError):
                negative = False
            if negative:
                findings.append(AnomalyFinding(
                    raw_secop_id=raw_secop_id,
                    motivo="MONTO_NEGATIVO",
                    valor_detectado=str(value),
                    tipo_anomalia="MONTO_NEGATIVO",
                    valor_original=str(value),
                    descripcion="El contrato contiene un monto negativo",
                    campo_afectado=field,
                ))

    return findings

def normalize_date(date_input: Any) -> date | None:
    if not date_input:
        return None
    
    if isinstance(date_input, date):
        if isinstance(date_input, datetime):
            return date_input.date()
        return date_input

    date_str = str(date_input).strip()
    if not date_str:
        return None

    # Try common formats
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
            
    # Try ISO formats with timezone or timestamps
    try:
        # e.g. 2023-01-01T00:00:00
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    return None

def normalize_amount(amount_input: Any) -> Decimal | None:
    if amount_input is None:
        return None
    
    if isinstance(amount_input, (Decimal, int, float)):
        return Decimal(str(amount_input))
        
    amount_str = str(amount_input)
    # Remove symbols, letters and whitespace
    amount_str = re.sub(r'[^\d.,-]', '', amount_str)
    
    # Handle European format vs US format
    # E.g. 1.000,50 vs 1,000.50
    # For simplicity, if we have both, assume last punctuation is decimal point
    if ',' in amount_str and '.' in amount_str:
        last_comma = amount_str.rfind(',')
        last_dot = amount_str.rfind('.')
        if last_comma > last_dot:
            # European format
            amount_str = amount_str.replace('.', '').replace(',', '.')
        else:
            # US format
            amount_str = amount_str.replace(',', '')
    else:
        # If only comma, assume it's a decimal separator if followed by 1-2 digits, otherwise thousands
        if ',' in amount_str:
            parts = amount_str.split(',')
            if len(parts[-1]) <= 2:
                amount_str = amount_str.replace(',', '.')
            else:
                amount_str = amount_str.replace(',', '')

    try:
        return Decimal(amount_str)
    except InvalidOperation:
        return None

def normalize_text(text_input: Any) -> str | None:
    if not text_input:
        return None
    
    # Remove invisible chars and convert to string
    text_str = str(text_input)
    
    # Remove newlines, tabs, etc
    text_str = re.sub(r'[\r\n\t]', ' ', text_str)
    
    # Remove extra spaces
    text_str = re.sub(r'\s+', ' ', text_str).strip()
    
    # Normalize case (UPPERCASE for standard consistency)
    return text_str.upper() if text_str else None


def normalize_provider_nit(nit_input: Any) -> str | None:
    """Normalize the source's supplier identifier without inferring identity.

    The source value is retained (uppercased and whitespace-normalized); known
    missing-value markers become None. We intentionally do not merge by name or
    strip punctuation, which could collapse distinct external identifiers.
    """
    nit = normalize_text(nit_input)
    if nit is None or nit in _IDENTIFICADORES_AUSENTES:
        return None
    return nit


def normalize_provider_nit_identity(nit_input: Any) -> str | None:
    """Return a join key only for a numeric NIT body with a valid optional DV.

    The returned key is the NIT body, because DIAN treats the verification
    digit as a separate field. The untouched normalized source value remains
    available through ``normalize_provider_nit`` for display and audit.
    """
    source = normalize_provider_nit(nit_input)
    if source is None:
        return None

    dv = None
    body = source
    if "-" in source:
        if source.count("-") != 1:
            return None
        body, dv = source.rsplit("-", 1)
        if len(dv) != 1 or not dv.isdigit():
            return None

    if body.isdigit():
        digits = body
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", body):
        digits = body.replace(".", "")
    elif re.fullmatch(r"\d{1,3}(?: \d{3})+", body):
        digits = body.replace(" ", "")
    else:
        return None

    if not 6 <= len(digits) <= 15:
        return None

    if dv is not None:
        weights = (71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3)
        weighted_sum = sum(
            int(digit) * weight
            for digit, weight in zip(digits, weights[-len(digits):])
        )
        remainder = weighted_sum % 11
        expected_dv = remainder if remainder in (0, 1) else 11 - remainder
        if int(dv) != expected_dv:
            return None

    return digits

def normalize_url(url_input: Any) -> str | None:
    if not url_input:
        return None
    
    url_str = str(url_input).strip()
    if not url_str:
        return None
        
    # Handle stringified dict like "{'url': 'https://...'}"
    if url_str.startswith("{") and url_str.endswith("}"):
        import ast
        try:
            parsed = ast.literal_eval(url_str)
            if isinstance(parsed, dict) and 'url' in parsed:
                return parsed['url']
        except (ValueError, SyntaxError):
            pass
            
        import re
        match = re.search(r"(https?://[^\s'}]+)", url_str)
        if match:
            return match.group(1)
            
    return url_str

def generate_hash(data: Dict[str, Any]) -> str:
    # Remove None values and created_at/updated_at to ensure consistent hashing of actual data
    cleaned_data = {
        k: str(v) for k, v in data.items() 
        if v is not None and k not in ['id', 'created_at', 'updated_at', 'normalized_hash']
    }
    
    # Sort keys for consistent JSON string
    json_str = json.dumps(cleaned_data, sort_keys=True)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
