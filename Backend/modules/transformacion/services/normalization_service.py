import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Any, Dict

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

def generate_hash(data: Dict[str, Any]) -> str:
    # Remove None values and created_at/updated_at to ensure consistent hashing of actual data
    cleaned_data = {
        k: str(v) for k, v in data.items() 
        if v is not None and k not in ['id', 'created_at', 'updated_at', 'normalized_hash']
    }
    
    # Sort keys for consistent JSON string
    json_str = json.dumps(cleaned_data, sort_keys=True)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
