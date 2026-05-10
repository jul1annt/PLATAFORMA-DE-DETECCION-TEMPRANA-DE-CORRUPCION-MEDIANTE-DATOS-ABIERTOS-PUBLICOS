import json
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
    SyncStatus
)
from modules.data_sources.patterns.factory import DataSourceConnectorFactory
from interfaces.data_sources_interface import DataSourcesInterface
from core.events.event_bus import event_bus
from core.events import event_types

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
        
        try:
            # Simulate fetch data
            data = await adapter.fetch_data()
            status = SyncStatus.SUCCESS
            
            # Publish event
            await event_bus.publish(
                event_types.DATA_FETCHED,
                {
                    "source_id": str(entity.id),
                    "source_type": entity.type.value if hasattr(entity.type, 'value') else entity.type,
                    "data": data
                }
            )
            
        except Exception:
            status = SyncStatus.FAILED
            
        # Update last sync status
        update_dto = DataSourceUpdateDTO()
        update_dto.last_sync_status = status
        # Since last_sync_at is not in UpdateDTO, we must update entity directly or add to DTO.
        # Actually it's better to update entity in the service or via repo.
        # Let's add last_sync_at to DTO if needed or just update it via a special method.
        # For now, let's update entity and save.
        entity.last_sync_at = datetime.now(timezone.utc)
        entity.last_sync_status = status
        
        await self.repository.session.commit()
        await self.repository.session.refresh(entity)

    async def sync_due_sources(self) -> None:
        due_sources = await self.repository.get_due_sources()
        for source in due_sources:
            await self.sync_source(source.id)
