from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from gateway.router import api_router
from gateway.middleware.logging import LoggingMiddleware
from gateway.middleware.auth import AuthMiddleware
from core.scheduler.scheduler import start_scheduler, stop_scheduler
from core.events.event_bus import event_bus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    event_bus.start()
    start_scheduler()
    yield
    # Shutdown
    logger.info("Shutting down application...")
    stop_scheduler()
    await event_bus.stop()

app = FastAPI(
    title="Data Sources API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middlewares
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)

# Routers
app.include_router(api_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
