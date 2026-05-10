import asyncio
from core.database import engine, Base

# Import all models so Base.metadata recognizes them
from modules.data_sources.models.entity import DataSource, SyncLog

async def init_db():
    async with engine.begin() as conn:
        print("Creando tablas en la base de datos...")
        await conn.run_sync(Base.metadata.create_all)
        print("¡Tablas creadas exitosamente!")

if __name__ == "__main__":
    asyncio.run(init_db())
