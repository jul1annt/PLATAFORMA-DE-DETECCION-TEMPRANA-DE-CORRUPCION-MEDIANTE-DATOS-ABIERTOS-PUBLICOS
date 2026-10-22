"""Explicit descriptive modality dictionary; never proves effective competition."""
import unicodedata
from .baseline_coverage import COMPETITIVE, NONCOMPETITIVE

CONTEXT_POLICY = 'selected-source-capture-rolling-v1'
DIRECT = NONCOMPETITIVE | {'CONTRATACION DIRECTA (CON OFERTAS)', 'CONTRATACION DIRECTA (SIN OFERTAS)'}
OTHER = COMPETITIVE


def direct_method(value):
    normalized = ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(value or '').upper())
                                 if not unicodedata.combining(c)).split())
    return True if normalized in DIRECT else False if normalized in OTHER else None
