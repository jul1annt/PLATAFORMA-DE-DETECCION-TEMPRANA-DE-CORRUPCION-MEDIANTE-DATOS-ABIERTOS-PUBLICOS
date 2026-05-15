from fastapi import APIRouter
from modules.ingesta.controller.IngestaController import router as ingesta_router
from modules.transformacion.controller.transformacionController import router as transformacion_router
from modules.analitica.controller.AnaliticaController import router as analitica_router
from modules.auth.controller.AuthController import router as auth_router


api_router = APIRouter(prefix="/api")
api_router.include_router(ingesta_router)
api_router.include_router(transformacion_router)
api_router.include_router(analitica_router)
api_router.include_router(auth_router)