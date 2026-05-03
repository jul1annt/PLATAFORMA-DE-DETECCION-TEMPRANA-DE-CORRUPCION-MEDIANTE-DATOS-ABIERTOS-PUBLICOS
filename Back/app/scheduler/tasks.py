from apscheduler.schedulers.background import BackgroundScheduler
from app.db.session import SessionLocal
from app.modules.ingestion.service import run_scheduled_ingestion

scheduler = BackgroundScheduler()

def scheduled_task():
    print("Running scheduled ingestion task...")
    db = SessionLocal()
    try:
        run_scheduled_ingestion(db)
    finally:
        db.close()

def start_scheduler():
    # Schedule the task to run every day, or at a specific interval 
    # (here we run it every 12 hours as a check, the service logic checks frequency rules)
    scheduler.add_job(scheduled_task, 'interval', hours=12, id='ingestion_job', replace_existing=True)
    scheduler.start()
    print("Scheduler started.")

def stop_scheduler():
    scheduler.shutdown()
    print("Scheduler stopped.")
