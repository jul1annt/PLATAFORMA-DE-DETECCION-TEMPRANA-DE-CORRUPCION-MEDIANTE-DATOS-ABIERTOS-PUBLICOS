from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from core.database import get_db
from gateway.middlewares.auth_middleware import get_current_admin
from modules.jobs.dto import BackgroundJobResponse, BackgroundJobStatusSummary
from modules.jobs.model import BackgroundJob
from modules.jobs.service import get_job_status_summary, to_job_response
from shared.request_validation import reject_unknown_query_params


router = APIRouter(
    prefix="/jobs",
    tags=["Trabajos"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("/resumen", response_model=BackgroundJobStatusSummary)
def get_jobs_summary(request: Request, db: Session = Depends(get_db)):
    reject_unknown_query_params(request, set())
    return get_job_status_summary(db)


@router.get("/{job_id}", response_model=BackgroundJobResponse)
def get_job(request: Request, job_id: UUID, db: Session = Depends(get_db)):
    reject_unknown_query_params(request, set())
    job = db.query(BackgroundJob).filter(BackgroundJob.public_id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trabajo no encontrado")
    return to_job_response(job)
