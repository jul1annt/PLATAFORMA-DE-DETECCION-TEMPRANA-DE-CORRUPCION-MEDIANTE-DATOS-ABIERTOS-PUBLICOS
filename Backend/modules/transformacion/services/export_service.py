"""Generate bounded contract exports outside the request process."""

import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import settings
from modules.transformacion.domain.filters import ContratoProcesadoFilter
from modules.transformacion.repository.transformacion import TransformacionRepository
from shared.export_artifacts import EXPORT_FORMATS, write_artifact
from shared.exporting import render_export


class ExportLimitExceededError(ValueError):
    """Raised when the matched export exceeds the configured row budget."""


def generate_contract_export(db: Session, job_id: UUID, payload: dict) -> dict:
    expires_at = int(payload["expires_at"])
    if int(time.time()) >= expires_at:
        raise ValueError("La solicitud de exportación venció antes de ejecutarse")

    fmt = payload["format"]
    if fmt not in EXPORT_FORMATS:
        raise ValueError("Formato de exportación inválido")
    filters = ContratoProcesadoFilter.model_validate(payload["filters"])
    sort = payload.get("sort")
    order = payload.get("order", "desc")
    if sort not in {
        None, "valor", "valor_total_normalizado", "precio_base_normalizado",
        "fecha", "id", "entidad", "proveedor", "riesgo",
    } or order not in {"asc", "desc"}:
        raise ValueError("Orden de exportación inválido")

    row_limit = min(settings.EXPORT_MAX_ROWS, 1000) if fmt == "pdf" else settings.EXPORT_MAX_ROWS
    items, total = TransformacionRepository(db).search_contratos(
        filters,
        skip=0,
        limit=row_limit + 1,
        sort=sort,
        order=order,
    )
    if total > row_limit or len(items) > row_limit:
        raise ExportLimitExceededError(
            f"La exportación supera el límite de {row_limit} registros"
        )

    columns = (
        "ID", "Entidad", "Proveedor", "Modalidad", "Valor total", "Fecha publicación",
        "Estado", "Confianza", "Incompleto", "Sospechoso", "Riesgo",
    )
    rows = (
        (
            item.id, item.entidad_normalizada, item.proveedor_normalizado,
            item.modalidad_contratacion, item.valor_total_normalizado,
            item.fecha_publicacion_normalizada, item.estado_normalizado,
            item.nivel_confianza, item.es_incompleto, item.es_sospechoso,
            item.clasificacion_riesgo,
        )
        for item in items
    )
    response = render_export(columns, rows, fmt, "contratos_calidad", "Contratos procesados")
    path, checksum = write_artifact(job_id, fmt, response.body)
    return {
        "format": fmt,
        "filename": f"contratos_calidad.{fmt}",
        "media_type": response.media_type,
        "row_count": total,
        "size_bytes": path.stat().st_size,
        "sha256": checksum,
        "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat(),
    }
