import logging
from core.database import AsyncSessionLocal
from modules.data_sources.repository import DataSourceRepository
from modules.data_sources.service import DataSourceService

logger = logging.getLogger(__name__)

async def run_sync_due_sources_job():
    logger.info("Running sync_due_sources job...")
    try:
        async with AsyncSessionLocal() as session:
            repository = DataSourceRepository(session)
            service = DataSourceService(repository)
            # The service implements DataSourcesInterface
            await service.sync_due_sources()
        logger.info("sync_due_sources job completed successfully.")
    except Exception as e:
        logger.error(f"Error in sync_due_sources job: {str(e)}")
