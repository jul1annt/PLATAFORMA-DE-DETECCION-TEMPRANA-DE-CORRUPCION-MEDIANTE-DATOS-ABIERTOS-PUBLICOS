from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.scheduler import iniciar_scheduler, scheduler
from gateway.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    iniciar_scheduler()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
app.include_router(api_router)