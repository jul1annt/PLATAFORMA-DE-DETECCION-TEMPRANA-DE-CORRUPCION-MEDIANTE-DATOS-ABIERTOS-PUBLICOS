from fastapi import APIRouter

from app.modules.fuentes.router import router as fuentes_router
from app.modules.ingestion.router import router as sync_router
from app.modules.logs.router import router as logs_router

api_router = APIRouter()

api_router.include_router(fuentes_router, prefix="/fuentes", tags=["Fuentes"])
api_router.include_router(sync_router, prefix="/sync", tags=["Sincronización"])
api_router.include_router(logs_router, prefix="/logs", tags=["Logs"])
