from datetime import date, datetime
from decimal import Decimal
from modules.transformacion.services.normalization_service import (
    normalize_date, normalize_amount, normalize_text, generate_hash
)

def test_normalize_date():
    # Valid ISO date
    assert normalize_date("2023-10-15") == date(2023, 10, 15)
    
    # Valid DD/MM/YYYY
    assert normalize_date("15/10/2023") == date(2023, 10, 15)
    
    # Valid DD-MM-YYYY
    assert normalize_date("15-10-2023") == date(2023, 10, 15)
    
    # Timestamps
    assert normalize_date("2023-10-15T12:00:00Z") == date(2023, 10, 15)
    
    # datetime object
    assert normalize_date(datetime(2023, 10, 15, 12, 0)) == date(2023, 10, 15)
    
    # Date object
    assert normalize_date(date(2023, 10, 15)) == date(2023, 10, 15)

    # Invalid cases
    assert normalize_date("invalid") is None
    assert normalize_date(None) is None
    assert normalize_date("") is None

def test_normalize_amount():
    # Symbols and spaces
    assert normalize_amount("$ 15000") == Decimal("15000")
    assert normalize_amount("COP 15000") == Decimal("15000")
    
    # Commas and dots - US Format
    assert normalize_amount("15,000.50") == Decimal("15000.50")
    
    # Commas and dots - EU Format
    assert normalize_amount("15.000,50") == Decimal("15000.50")
    
    # Only commas
    assert normalize_amount("15,000") == Decimal("15000")
    assert normalize_amount("15,50") == Decimal("15.50") # less than 2 digits assumes decimals
    
    # Clean decimals
    assert normalize_amount(15000.50) == Decimal("15000.5")
    assert normalize_amount(Decimal("15000.50")) == Decimal("15000.50")
    
    # Invalid cases
    assert normalize_amount("invalid") is None
    assert normalize_amount(None) is None

def test_normalize_text():
    # Extra spaces
    assert normalize_text("  Texto   con  espacios  ") == "TEXTO CON ESPACIOS"
    
    # Invisible chars (tabs, newlines)
    assert normalize_text("Texto\ncon\ttabs") == "TEXTO CON TABS"
    
    # Mixed case
    assert normalize_text("TeXto MiXtO") == "TEXTO MIXTO"
    
    # Null values
    assert normalize_text(None) is None
    assert normalize_text("") is None

def test_generate_hash():
    data1 = {"entidad": "ALCALDIA", "valor": "1000", "id": 1, "created_at": "2023-01-01"}
    data2 = {"valor": "1000", "entidad": "ALCALDIA", "id": 2, "updated_at": "2023-01-01"}
    
    # Hashes should match regardless of key order, or ignored fields like id/created_at
    assert generate_hash(data1) == generate_hash(data2)
    
    data3 = {"entidad": "GOBERNACION", "valor": "1000"}
    assert generate_hash(data1) != generate_hash(data3)
