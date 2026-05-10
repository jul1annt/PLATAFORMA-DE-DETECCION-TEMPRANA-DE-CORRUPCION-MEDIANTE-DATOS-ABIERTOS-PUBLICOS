from sqlalchemy import Column, String, Integer, Boolean, DateTime, func, JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from datetime import datetime

from core.database import Base
from modules.data_sources.models.dto import DataSourceType, SyncStatus

class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    type = Column(SAEnum(DataSourceType), nullable=False)
    endpoint_url = Column(String, nullable=False)
    credentials = Column(String, nullable=True) # Will store encrypted string
    frequency_days = Column(Integer, default=15)
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_status = Column(SAEnum(SyncStatus), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
