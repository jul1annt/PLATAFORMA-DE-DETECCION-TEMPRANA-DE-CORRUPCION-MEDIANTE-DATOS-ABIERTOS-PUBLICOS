from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.init_db import init_db
from app.api.router import api_router
from app.scheduler.tasks import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initializing Database...")
    init_db()
    print("Starting Scheduler...")
    start_scheduler()
    yield
    # Shutdown
    print("Stopping Scheduler...")
    stop_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend for Epic 1: Ingestión de Datos - Plataforma Anticorrupción",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Bienvenido a la API de la Plataforma Anticorrupción - Epic 1"}
