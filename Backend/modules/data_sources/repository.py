from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, tuple_

from modules.data_sources.models.entity import DataSource, SyncLog
from modules.data_sources.models.dto import DataSourceCreateDTO, DataSourceUpdateDTO, LogStatus

class DataSourceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, dto: DataSourceCreateDTO) -> DataSource:
        entity = DataSource(
            name=dto.name,
            type=dto.type,
            endpoint_url=dto.endpoint_url,
            credentials=dto.credentials,
            frequency_days=dto.frequency_days
        )
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def get_by_id(self, id: UUID) -> Optional[DataSource]:
        stmt = select(DataSource).where(DataSource.id == id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all(self) -> List[DataSource]:
        stmt = select(DataSource).order_by(DataSource.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, id: UUID, dto: DataSourceUpdateDTO) -> Optional[DataSource]:
        entity = await self.get_by_id(id)
        if not entity:
            return None

        update_data = dto.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(entity, key, value)
            
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> bool:
        entity = await self.get_by_id(id)
        if not entity:
            return False
        
        await self.session.delete(entity)
        await self.session.commit()
        return True

    async def get_due_sources(self) -> List[DataSource]:
        now = datetime.now(timezone.utc)
        
        # Sources are due if:
        # 1. They are active AND
        # 2. They have never been synced OR
        #    Their last_sync_at + frequency_days <= now
        
        # We need to construct the date math. For simplicity and cross-DB compatibility,
        # we can fetch active ones and filter in python if the DB date math is complex.
        # But we can try to do it in SQLAlchemy. Since SQLite and PostgreSQL differ slightly 
        # on timedelta, let's just fetch active ones and filter in python if needed, 
        # or use native datetime.
        
        stmt = select(DataSource).where(DataSource.is_active == True)
        result = await self.session.execute(stmt)
        active_sources = result.scalars().all()
        
        due_sources = []
        for source in active_sources:
            if source.last_sync_at is None:
                due_sources.append(source)
            else:
                next_sync = source.last_sync_at + timedelta(days=source.frequency_days)
                if next_sync <= now:
                    due_sources.append(source)
                    
        return due_sources

    # ── Sync Log methods ────────────────────────────────────────────────────

    async def create_sync_log(self, source_id: UUID) -> SyncLog:
        """Create a sync log entry with status IN_PROGRESS."""
        log = SyncLog(
            source_id=source_id,
            started_at=datetime.now(timezone.utc),
            status=LogStatus.IN_PROGRESS,
            attempt_number=1,
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def update_sync_log(
        self,
        log_id: UUID,
        status: LogStatus,
        finished_at: datetime,
        records_fetched: Optional[int] = None,
        error_message: Optional[str] = None,
        attempt_number: int = 1,
    ) -> Optional[SyncLog]:
        """Update a sync log entry after a sync attempt concludes."""
        stmt = select(SyncLog).where(SyncLog.id == log_id)
        result = await self.session.execute(stmt)
        log = result.scalars().first()
        if not log:
            return None
        log.status = status
        log.finished_at = finished_at
        log.records_fetched = records_fetched
        log.error_message = error_message
        log.attempt_number = attempt_number
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def get_logs_by_source(self, source_id: UUID) -> List[SyncLog]:
        """Return all sync logs for a given source ordered by started_at DESC."""
        stmt = (
            select(SyncLog)
            .where(SyncLog.source_id == source_id)
            .order_by(SyncLog.started_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_logs(self) -> List[SyncLog]:
        """Return all sync logs across every source ordered by started_at DESC."""
        stmt = select(SyncLog).order_by(SyncLog.started_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
