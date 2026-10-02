"""Capability-protected status and download endpoints for public exports."""

import time
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from core.database import get_db
from modules.jobs.dto import ExportJobStatus
from modules.jobs.model import BackgroundJob
from shared.export_artifacts import artifact_path, parse_export_token
from shared.request_validation import reject_unknown_query_params


router = APIRouter(prefix="/exports", tags=["Exportaciones"])
MEDIA_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def _authorized_export(
    request: Request,
    job_id: UUID,
    token: str | None,
    db: Session,
) -> BackgroundJob:
    reject_unknown_query_params(request, set())
    expires_at = parse_export_token(job_id, token)
    if expires_at is None:
        raise HTTPException(status_code=404, detail="Exportación no encontrada")
    if int(time.time()) >= expires_at:
        for fmt in ("csv", "xlsx", "pdf"):
            artifact_path(job_id, fmt).unlink(missing_ok=True)
        raise HTTPException(status_code=410, detail="El enlace de descarga venció")

    job = db.query(BackgroundJob).filter(BackgroundJob.public_id == job_id).first()
    if (
        job is None
        or job.kind != "EXPORTACION_CONTRATOS"
        or int(job.payload.get("expires_at", 0)) != expires_at
    ):
        raise HTTPException(status_code=404, detail="Exportación no encontrada")
    return job


@router.get("/{job_id}", response_model=ExportJobStatus)
def get_export_status(
    request: Request,
    job_id: UUID,
    response: Response,
    token: str | None = Header(default=None, alias="X-Export-Token"),
    db: Session = Depends(get_db),
):
    job = _authorized_export(request, job_id, token, db)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return ExportJobStatus(
        id=job.public_id,
        status=job.status,
        created_at=job.created_at,
        result=job.result,
        error_message=job.error_message,
    )


@router.get("/{job_id}/download")
def download_export(
    request: Request,
    job_id: UUID,
    token: str | None = Header(default=None, alias="X-Export-Token"),
    db: Session = Depends(get_db),
):
    job = _authorized_export(request, job_id, token, db)
    if job.status != "EXITOSO" or not job.result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La exportación todavía no está disponible",
        )

    fmt = job.result.get("format")
    try:
        path = artifact_path(job.public_id, fmt)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Archivo de exportación no encontrado") from exc
    if not path.is_file():
        raise HTTPException(status_code=410, detail="El archivo de exportación ya no está disponible")

    return FileResponse(
        path,
        media_type=MEDIA_TYPES[fmt],
        filename=f"contratos_calidad.{fmt}",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
