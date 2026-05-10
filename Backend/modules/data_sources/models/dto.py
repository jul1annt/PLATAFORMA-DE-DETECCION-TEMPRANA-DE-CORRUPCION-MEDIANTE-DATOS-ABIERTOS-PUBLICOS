from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any
from uuid import UUID
from datetime import datetime
from enum import Enum

class DataSourceType(str, Enum):
    SECOP = "SECOP"
    SISCON = "SISCON"

class SyncStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class DataSourceCreateDTO(BaseModel):
    name: str
    type: DataSourceType
    endpoint_url: str
    credentials: Optional[dict[str, Any]] = None
    frequency_days: int = Field(default=15, ge=1)

class DataSourceUpdateDTO(BaseModel):
    name: Optional[str] = None
    type: Optional[DataSourceType] = None
    endpoint_url: Optional[str] = None
    credentials: Optional[dict[str, Any]] = None
    frequency_days: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None

class DataSourceResponseDTO(BaseModel):
    id: UUID
    name: str
    type: DataSourceType
    endpoint_url: str
    frequency_days: int
    is_active: bool
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[SyncStatus] = None
    
    model_config = ConfigDict(from_attributes=True)

class DataSourceTestResultDTO(BaseModel):
    success: bool
    message: str
    response_time_ms: Optional[int] = None
