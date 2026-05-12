from fastapi import APIRouter
from modules.ingesta.controller.IngestaController import router as ingesta_router
from modules.transformacion.controller.transformacionController import router as transformacion_router

api_router = APIRouter(prefix="/api")
api_router.include_router(ingesta_router)
api_router.include_router(transformacion_router)