from typing import Protocol
from uuid import UUID
from modules.data_sources.models.dto import DataSourceTestResultDTO

class DataSourcesInterface(Protocol):
    async def sync_due_sources(self) -> None:
        ...

    async def test_connection(self, source_id: UUID) -> DataSourceTestResultDTO:
        ...
