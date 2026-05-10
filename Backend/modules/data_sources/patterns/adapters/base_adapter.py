from abc import ABC, abstractmethod
from modules.data_sources.models.dto import DataSourceTestResultDTO

class BaseAdapter(ABC):
    @abstractmethod
    async def test_connection(self) -> DataSourceTestResultDTO:
        pass

    @abstractmethod
    async def fetch_data(self) -> dict:
        pass
