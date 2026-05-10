from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.scheduler.jobs.sync_job import run_sync_due_sources_job
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def start_scheduler():
    logger.info("Starting scheduler...")
    # Add the sync job to run every hour
    scheduler.add_job(run_sync_due_sources_job, 'interval', hours=1, id='sync_due_sources_job')
    scheduler.start()

def stop_scheduler():
    logger.info("Stopping scheduler...")
    scheduler.shutdown()
