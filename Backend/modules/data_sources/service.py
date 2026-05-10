import asyncio
import json
import logging
from uuid import UUID
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from typing import List

from core.config import settings
from core.exceptions import NotFoundException
from modules.data_sources.repository import DataSourceRepository
from modules.data_sources.models.dto import (
    DataSourceCreateDTO,
    DataSourceUpdateDTO,
    DataSourceTestResultDTO,
    SyncStatus,
    LogStatus,
    SyncLogResponseDTO,
)
from modules.data_sources.patterns.factory import DataSourceConnectorFactory
from interfaces.data_sources_interface import DataSourcesInterface
from core.events.event_bus import event_bus
from core.events import event_types

logger = logging.getLogger(__name__)

class DataSourceService(DataSourcesInterface):
    def __init__(self, repository: DataSourceRepository):
        self.repository = repository
        self.fernet = Fernet(settings.ENCRYPTION_KEY.encode())

    def _encrypt_credentials(self, credentials: dict | None) -> str | None:
        if not credentials:
            return None
        return self.fernet.encrypt(json.dumps(credentials).encode()).decode()

    def _decrypt_credentials(self, encrypted_credentials: str | None) -> dict | None:
        if not encrypted_credentials:
            return None
        return json.loads(self.fernet.decrypt(encrypted_credentials.encode()).decode())

    async def create_source(self, dto: DataSourceCreateDTO):
        if dto.credentials:
            # DTO has a dict for credentials, we need to convert it to encrypted string before saving.
            # But wait, DTO definition is credentials: dict. 
            # We can either change the DTO in the method or map it before repository call.
            # We'll map it to the entity by letting the repository take the DTO, but the DTO expects dict.
            # We should probably encrypt it here, and pass a new DTO or modify it.
            dto.credentials = self._encrypt_credentials(dto.credentials) # Note: DB model expects JSON but we store a string?
            # Actually, if the DB model expects JSON, but we encrypt, it becomes a string.
            # Let's adjust this: we store a string in the DB.
            pass
            
        # The Repository takes the DTO directly.
        entity = await self.repository.create(dto)
        return entity

    async def get_source(self, id: UUID):
        entity = await self.repository.get_by_id(id)
        if not entity:
            raise NotFoundException("Data source not found")
        return entity

    async def get_all_sources(self):
        return await self.repository.get_all()

    async def update_source(self, id: UUID, dto: DataSourceUpdateDTO):
        if dto.credentials is not None:
            dto.credentials = self._encrypt_credentials(dto.credentials)
            
        entity = await self.repository.update(id, dto)
        if not entity:
            raise NotFoundException("Data source not found")
        return entity

    async def delete_source(self, id: UUID):
        success = await self.repository.delete(id)
        if not success:
            raise NotFoundException("Data source not found")
        return success

    async def test_connection(self, source_id: UUID) -> DataSourceTestResultDTO:
        entity = await self.get_source(source_id)
        credentials = self._decrypt_credentials(entity.credentials) if isinstance(entity.credentials, str) else entity.credentials
        
        adapter = DataSourceConnectorFactory.get_adapter(
            source_type=entity.type,
            endpoint_url=entity.endpoint_url,
            credentials=credentials
        )
        return await adapter.test_connection()

    async def sync_source(self, id: UUID):
        entity = await self.get_source(id)
        credentials = self._decrypt_credentials(entity.credentials) if isinstance(entity.credentials, str) else entity.credentials

        adapter = DataSourceConnectorFactory.get_adapter(
            source_type=entity.type,
            endpoint_url=entity.endpoint_url,
            credentials=credentials
        )

        max_retries = settings.MAX_SYNC_RETRIES
        retry_delay = settings.SYNC_RETRY_DELAY_SECONDS

        # Create log with IN_PROGRESS status at the start
        sync_log = await self.repository.create_sync_log(source_id=entity.id)

        data = None
        last_error: str | None = None
        attempt = 0

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Sync attempt {attempt}/{max_retries} for source {entity.id}")
                data = await adapter.fetch_data()
                last_error = None
                break  # Success — exit retry loop
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    f"Sync attempt {attempt}/{max_retries} failed for source {entity.id}: {last_error}"
                )
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)

        finished_at = datetime.now(timezone.utc)

        if last_error is not None:
            # All attempts failed
            await self.repository.update_sync_log(
                log_id=sync_log.id,
                status=LogStatus.FAILED,
                finished_at=finished_at,
                error_message=last_error,
                attempt_number=attempt,
            )
            entity.last_sync_at = finished_at
            entity.last_sync_status = SyncStatus.FAILED
            await self.repository.session.commit()
            await self.repository.session.refresh(entity)
            logger.error(
                f"Sync for source {entity.id} failed after {attempt} attempt(s): {last_error}"
            )
            return

        # Successful sync
        records_fetched = len(data) if isinstance(data, (list, dict)) else None

        await self.repository.update_sync_log(
            log_id=sync_log.id,
            status=LogStatus.SUCCESS,
            finished_at=finished_at,
            records_fetched=records_fetched,
            attempt_number=attempt,
        )

        entity.last_sync_at = finished_at
        entity.last_sync_status = SyncStatus.SUCCESS
        await self.repository.session.commit()
        await self.repository.session.refresh(entity)

        # Publish DATA_FETCHED event
        await event_bus.publish(
            event_types.DATA_FETCHED,
            {
                "source_id": str(entity.id),
                "source_type": entity.type.value if hasattr(entity.type, "value") else entity.type,
                "data": data,
            }
        )
        logger.info(
            f"Sync for source {entity.id} succeeded on attempt {attempt}. "
            f"Records fetched: {records_fetched}"
        )

    async def sync_due_sources(self) -> None:
        due_sources = await self.repository.get_due_sources()
        for source in due_sources:
            await self.sync_source(source.id)

    async def get_sync_logs(self, source_id: UUID) -> List[SyncLogResponseDTO]:
        await self.get_source(source_id)  # raises NotFoundException if not found
        logs = await self.repository.get_logs_by_source(source_id)
        return [SyncLogResponseDTO.model_validate(log) for log in logs]

    async def get_all_sync_logs(self) -> List[SyncLogResponseDTO]:
        logs = await self.repository.get_all_logs()
        return [SyncLogResponseDTO.model_validate(log) for log in logs]
