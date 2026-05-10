import httpx
import time
from modules.data_sources.patterns.adapters.base_adapter import BaseAdapter
from modules.data_sources.models.dto import DataSourceTestResultDTO

class SisconAdapter(BaseAdapter):
    def __init__(self, endpoint_url: str, credentials: dict | None = None):
        self.endpoint_url = endpoint_url
        self.credentials = credentials

    async def test_connection(self) -> DataSourceTestResultDTO:
        start_time = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.endpoint_url, timeout=10.0)
                response.raise_for_status()
                end_time = time.time()
                return DataSourceTestResultDTO(
                    success=True,
                    message="Connection to SISCON successful",
                    response_time_ms=int((end_time - start_time) * 1000)
                )
        except Exception as e:
            end_time = time.time()
            return DataSourceTestResultDTO(
                success=False,
                message=f"Connection failed: {str(e)}",
                response_time_ms=int((end_time - start_time) * 1000)
            )

    async def fetch_data(self) -> dict:
        # Placeholder for real data fetching logic
        return {"source": "SISCON", "data": []}
