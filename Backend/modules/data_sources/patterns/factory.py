from modules.data_sources.models.dto import DataSourceType
from modules.data_sources.patterns.adapters.base_adapter import BaseAdapter
from modules.data_sources.patterns.adapters.secop_adapter import SecopAdapter
from modules.data_sources.patterns.adapters.siscon_adapter import SisconAdapter

class DataSourceConnectorFactory:
    @staticmethod
    def get_adapter(source_type: DataSourceType, endpoint_url: str, credentials: dict | None = None) -> BaseAdapter:
        if source_type == DataSourceType.SECOP:
            return SecopAdapter(endpoint_url, credentials)
        elif source_type == DataSourceType.SISCON:
            return SisconAdapter(endpoint_url, credentials)
        else:
            raise ValueError(f"Unknown data source type: {source_type}")
