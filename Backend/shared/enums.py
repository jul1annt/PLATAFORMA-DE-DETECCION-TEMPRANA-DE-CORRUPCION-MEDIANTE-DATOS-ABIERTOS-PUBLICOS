from enum import Enum

class TipoFormato(str, Enum):
    JSON = "JSON"
    CSV  = "CSV"
    XML  = "XML"