from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, func, JSON, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from core.database import Base
from modules.data_sources.models.dto import DataSourceType, SyncStatus, LogStatus

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

    sync_logs = relationship("SyncLog", back_populates="data_source", cascade="all, delete-orphan")


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(PG_UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(SAEnum(LogStatus), nullable=False)
    records_fetched = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    attempt_number = Column(Integer, default=1, nullable=False)

    data_source = relationship("DataSource", back_populates="sync_logs")
