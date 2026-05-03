from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors.
    """
    
    @abstractmethod
    def fetch_data(self, endpoint: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetches data from the given endpoint.
        
        :param endpoint: The URL or identifier of the data source.
        :return: A list of dictionaries representing the raw data records.
        """
        pass
