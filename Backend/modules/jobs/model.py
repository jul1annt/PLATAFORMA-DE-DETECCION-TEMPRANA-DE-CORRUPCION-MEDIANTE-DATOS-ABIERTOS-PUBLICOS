import uuid

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, BigInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from shared.base_model import Base


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    public_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    resource_key = Column(String(160), nullable=True)
    kind = Column(String(40), nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False, default="PENDIENTE", server_default="PENDIENTE")
    active = Column(Boolean, nullable=False, default=True, server_default="true")
    attempts = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(JSONB, nullable=True)
    error_id = Column(UUID(as_uuid=True), nullable=True)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_background_jobs_dispatch", "status", "created_at"),
        Index(
            "uq_background_jobs_active_resource",
            "resource_key",
            unique=True,
            postgresql_where=resource_key.is_not(None) & active.is_(True),
        ),
    )
