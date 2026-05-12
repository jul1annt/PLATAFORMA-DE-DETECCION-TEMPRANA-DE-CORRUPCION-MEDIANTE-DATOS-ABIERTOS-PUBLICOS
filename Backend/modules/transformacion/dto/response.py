from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

# ──────────────────────────────────────────────
# RESPUESTA: Contrato Procesado
# ──────────────────────────────────────────────
class ContratoProcesadoResponseDTO(BaseModel):
    id: int = Field(..., description="ID único del registro procesado")
    raw_secop_id: int = Field(..., description="Referencia al ID original en raw_secop")

    id_del_proceso: Optional[str] = Field(None, description="Identificador único del proceso de contratación")
    entidad_normalizada: Optional[str] = Field(None, description="Nombre de la entidad normalizado")
    nit_entidad: Optional[str] = Field(None, description="NIT de la entidad")
    proveedor_normalizado: Optional[str] = Field(None, description="Nombre del proveedor normalizado")
    nit_proveedor: Optional[str] = Field(None, description="NIT del proveedor adjudicado")
    fecha_publicacion_normalizada: Optional[date] = Field(None, description="Fecha de publicación en ISO 8601 (YYYY-MM-DD)")
    fecha_adjudicacion_normalizada: Optional[date] = Field(None, description="Fecha de adjudicación en ISO 8601 (YYYY-MM-DD)")
    valor_total_normalizado: Optional[Decimal] = Field(None, description="Valor total del contrato como número limpio")
    precio_base_normalizado: Optional[Decimal] = Field(None, description="Precio base normalizado")
    tipo_contrato_normalizado: Optional[str] = Field(None, description="Tipo de contrato normalizado")
    modalidad_contratacion: Optional[str] = Field(None, description="Modalidad de contratación normalizada")
    estado_normalizado: Optional[str] = Field(None, description="Estado del procedimiento normalizado")
    ciudad_entidad: Optional[str] = Field(None, description="Ciudad de la entidad")
    departamento_entidad: Optional[str] = Field(None, description="Departamento de la entidad")
    urlproceso: Optional[str] = Field(None, description="URL del proceso en SECOP")
    normalized_hash: str = Field(..., description="Hash SHA256 del contenido normalizado")
    created_at: datetime = Field(..., description="Fecha de creación del registro")

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────
# RESPUESTA: Anomalía detectada
# ──────────────────────────────────────────────
class AnomaliaResponseDTO(BaseModel):
    id: int = Field(..., description="ID de la anomalía")
    raw_secop_id: int = Field(..., description="ID del registro crudo que presentó la anomalía")
    motivo: str = Field(..., description="Tipo de anomalía: CAMPO_FALTANTE | FECHA_FUTURA | MONTO_NEGATIVO")
    campo_afectado: str = Field(..., description="Nombre del campo donde se detectó la anomalía")
    valor_detectado: Optional[str] = Field(None, description="Valor que disparó la anomalía (puede ser NULL si el campo está vacío)")
    created_at: datetime = Field(..., description="Fecha de registro de la anomalía")

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────
# RESPUESTA: Estadísticas de campos faltantes
# ──────────────────────────────────────────────
class EstadisticaCampoResponseDTO(BaseModel):
    id: int = Field(..., description="ID del registro")
    nombre_campo: str = Field(..., description="Nombre del campo obligatorio")
    contador_faltantes: int = Field(..., description="Cantidad de veces que faltó este campo")
    updated_at: Optional[datetime] = Field(None, description="Última vez que se actualizó el contador")

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────
# RESPUESTAS: Paginación genérica
# ──────────────────────────────────────────────
class PaginatedContratosDTO(BaseModel):
    total: int
    page: int
    size: int
    items: List[ContratoProcesadoResponseDTO]

class PaginatedAnomaliasDTO(BaseModel):
    total: int
    page: int
    size: int
    items: List[AnomaliaResponseDTO]


# ──────────────────────────────────────────────
# RESPUESTA: Resultado del reprocesamiento
# ──────────────────────────────────────────────
class ReprocesarResultadoDTO(BaseModel):
    total_evaluados: int = Field(..., description="Total de registros crudos evaluados")
    procesados: int = Field(..., description="Registros que se normalizaron correctamente")
    omitidos: int = Field(..., description="Registros omitidos (ya existían con el mismo hash)")
    anomalias_registradas: int = Field(..., description="Total de anomalías detectadas y guardadas")
