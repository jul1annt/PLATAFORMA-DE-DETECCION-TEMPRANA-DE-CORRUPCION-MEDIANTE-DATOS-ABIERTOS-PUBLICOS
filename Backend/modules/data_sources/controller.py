from fastapi import APIRouter, Depends, status, HTTPException
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import NotFoundException
from modules.data_sources.models.dto import (
    DataSourceCreateDTO,
    DataSourceUpdateDTO,
    DataSourceResponseDTO,
    DataSourceTestResultDTO,
    SyncLogResponseDTO,
)
from modules.data_sources.repository import DataSourceRepository
from modules.data_sources.service import DataSourceService

router = APIRouter(prefix="/data-sources", tags=["data-sources"])

def get_service(session: AsyncSession = Depends(get_db)) -> DataSourceService:
    repository = DataSourceRepository(session)
    return DataSourceService(repository)

@router.post("/", response_model=DataSourceResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_data_source(dto: DataSourceCreateDTO, service: DataSourceService = Depends(get_service)):
    return await service.create_source(dto)

@router.get("/", response_model=List[DataSourceResponseDTO])
async def get_all_data_sources(service: DataSourceService = Depends(get_service)):
    return await service.get_all_sources()

@router.get("/{id}", response_model=DataSourceResponseDTO)
async def get_data_source(id: UUID, service: DataSourceService = Depends(get_service)):
    return await service.get_source(id)

@router.put("/{id}", response_model=DataSourceResponseDTO)
async def update_data_source(id: UUID, dto: DataSourceUpdateDTO, service: DataSourceService = Depends(get_service)):
    return await service.update_source(id, dto)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(id: UUID, service: DataSourceService = Depends(get_service)):
    await service.delete_source(id)
    return None

@router.post("/{id}/test", response_model=DataSourceTestResultDTO)
async def test_connection(id: UUID, service: DataSourceService = Depends(get_service)):
    return await service.test_connection(id)

@router.post("/{id}/sync", status_code=status.HTTP_200_OK)
async def sync_data_source(id: UUID, service: DataSourceService = Depends(get_service)):
    await service.sync_source(id)
    return {"detail": "Sync successful"}

# ── Sync Log endpoints ────────────────────────────────────────────────────
# NOTE: /logs must be declared BEFORE /{id} to avoid FastAPI treating
# the literal string "logs" as a UUID path parameter.

@router.get("/logs", response_model=List[SyncLogResponseDTO], tags=["sync-logs"])
async def get_all_sync_logs(service: DataSourceService = Depends(get_service)):
    """Return sync history for all data sources."""
    return await service.get_all_sync_logs()

@router.get("/{id}/logs", response_model=List[SyncLogResponseDTO], tags=["sync-logs"])
async def get_sync_logs_by_source(
    id: UUID,
    service: DataSourceService = Depends(get_service),
):
    """Return sync history for a specific data source."""
    try:
        return await service.get_sync_logs(id)
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {id} not found",
        )
