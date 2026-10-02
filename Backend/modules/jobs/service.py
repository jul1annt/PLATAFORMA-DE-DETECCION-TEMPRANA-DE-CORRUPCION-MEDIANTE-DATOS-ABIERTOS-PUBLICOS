from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlalchemy.orm import Session

from modules.jobs.dto import (
    BackgroundJobAccepted,
    BackgroundJobResponse,
    BackgroundJobStatusSummary,
)
from modules.jobs.model import BackgroundJob


def enqueue_job(
    db: Session,
    *,
    kind: str,
    payload: dict,
    resource_key: str,
) -> tuple[BackgroundJob, bool]:
    existing = db.query(BackgroundJob).filter(
        BackgroundJob.resource_key == resource_key,
        BackgroundJob.active.is_(True),
    ).first()
    if existing:
        return existing, False

    job = BackgroundJob(
        kind=kind,
        payload=payload,
        resource_key=resource_key,
        status="PENDIENTE",
        active=True,
    )
    db.add(job)
    try:
        db.commit()
        db.refresh(job)
        return job, True
    except IntegrityError:
        db.rollback()
        # Another API or scheduler process enqueued the same resource first.
        existing = db.query(BackgroundJob).filter(
            BackgroundJob.resource_key == resource_key,
            BackgroundJob.active.is_(True),
        ).first()
        if existing:
            return existing, False
        raise


def to_job_response(job: BackgroundJob) -> BackgroundJobResponse:
    return BackgroundJobResponse(
        id=job.public_id,
        kind=job.kind,
        status=job.status,
        attempts=job.attempts,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        result=job.result,
        error_id=job.error_id,
        error_message=job.error_message,
    )


def to_job_accepted(job: BackgroundJob) -> BackgroundJobAccepted:
    return BackgroundJobAccepted(
        id=job.public_id,
        kind=job.kind,
        status=job.status,
        status_url=f"/api/jobs/{job.public_id}",
    )


def get_job_status_summary(db: Session) -> BackgroundJobStatusSummary:
    rows = db.query(
        BackgroundJob.status,
        func.count(BackgroundJob.id),
    ).group_by(BackgroundJob.status).all()
    counts = {str(status): int(count) for status, count in rows}
    return BackgroundJobStatusSummary(
        total=sum(counts.values()),
        by_status=counts,
    )
