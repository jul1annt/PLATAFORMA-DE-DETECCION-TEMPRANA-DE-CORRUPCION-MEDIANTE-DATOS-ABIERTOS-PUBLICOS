from fastapi import APIRouter
from modules.ingesta.controller.IngestaController import router as ingesta_router

api_router = APIRouter(prefix="/api")
api_router.include_router(ingesta_router)