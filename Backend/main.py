from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from gateway.router import api_router
from gateway.http_errors import auth_error_response, ingesta_error_response
from shared.errors import AuthError, IngestaError

app = FastAPI(
    title="Plataforma Detección Temprana de Corrupción",
    version="1.0.0",
)

app.add_exception_handler(AuthError, auth_error_response)
app.add_exception_handler(IngestaError, ingesta_error_response)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Accept", "Authorization", "Content-Type", "X-Export-Token"],
)

app.include_router(api_router)
