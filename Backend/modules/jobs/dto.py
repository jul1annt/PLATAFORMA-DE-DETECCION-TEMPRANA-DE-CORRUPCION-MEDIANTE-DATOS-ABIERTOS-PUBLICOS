from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class BackgroundJobResponse(BaseModel):
    id: UUID
    kind: str
    status: Literal["PENDIENTE", "EN_PROCESO", "PARCIAL", "EXITOSO", "ERROR"]
    attempts: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result: dict[str, Any] | None
    error_id: UUID | None
    error_message: str | None


class BackgroundJobStatusSummary(BaseModel):
    total: int
    by_status: dict[str, int]


class BackgroundJobAccepted(BaseModel):
    id: UUID
    kind: str
    status: Literal["PENDIENTE", "EN_PROCESO", "EXITOSO", "ERROR"]
    status_url: str


class ExportJobAccepted(BaseModel):
    id: UUID
    status: Literal["PENDIENTE", "EN_PROCESO", "EXITOSO", "ERROR"]
    access_token: str
    status_url: str
    download_url: str
    expires_at: datetime


class ExportJobStatus(BaseModel):
    id: UUID
    status: Literal["PENDIENTE", "EN_PROCESO", "EXITOSO", "ERROR"]
    created_at: datetime
    result: dict[str, Any] | None
    error_message: str | None
