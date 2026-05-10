from fastapi import APIRouter
from modules.data_sources.controller import router as data_sources_router

api_router = APIRouter(prefix="/api")

api_router.include_router(data_sources_router)
