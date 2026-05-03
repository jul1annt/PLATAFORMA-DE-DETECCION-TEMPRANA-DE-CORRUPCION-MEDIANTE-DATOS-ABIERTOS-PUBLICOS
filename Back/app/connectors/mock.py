from typing import List, Dict, Any
from app.connectors.base import BaseConnector
import random
import uuid

class MockConnector(BaseConnector):
    """
    Simulates fetching data from a public contracting API like SECOP.
    """
    def fetch_data(self, endpoint: str, **kwargs) -> List[Dict[str, Any]]:
        print(f"Mock fetching data from {endpoint}...")
        
        # Simulating a batch of 5 to 15 random records
        num_records = random.randint(5, 15)
        records = []
        for _ in range(num_records):
            record = {
                "id_proceso": f"CO1.BDOS.{random.randint(1000000, 9999999)}",
                "referencia_proceso": f"REF-{uuid.uuid4().hex[:8].upper()}",
                "estado_procedimiento": random.choice(["Adjudicado", "En evaluación", "Borrador", "Cerrado"]),
                "entidad": {
                    "nit": f"800{random.randint(100000, 999999)}-{random.randint(1,9)}",
                    "nombre": random.choice(["Alcaldía Local", "Gobernación", "Ministerio de Educación"])
                },
                "valor_total": random.randint(1000000, 500000000),
                "url_proceso": f"https://mock-secop.gov.co/{uuid.uuid4().hex}"
            }
            records.append(record)
            
        return records
