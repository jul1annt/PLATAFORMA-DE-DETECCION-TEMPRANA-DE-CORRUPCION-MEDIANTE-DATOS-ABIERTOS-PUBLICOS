from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.scheduler import iniciar_scheduler, scheduler
from gateway.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    iniciar_scheduler()
    yield
    scheduler.shutdown()

app = FastAPI(
    title="Plataforma Detección Temprana de Corrupción",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)