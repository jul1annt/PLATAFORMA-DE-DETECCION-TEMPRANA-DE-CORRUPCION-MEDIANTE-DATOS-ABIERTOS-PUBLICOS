from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.database import get_db
from modules.auth.service.AuthService import AuthService
from modules.auth.dto.request import LoginRequest, CreateAdminRequest
from modules.auth.dto.response import TokenResponse, AdminResponse, MessageResponse
from gateway.middlewares.auth_middleware import get_current_admin

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return AuthService(db).login(data)

@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def logout(current_admin: AdminResponse = Depends(get_current_admin)):
    # El logout es stateless con JWT: el front elimina el token.
    # Si necesitas blacklist de tokens, se extiende aquí con Redis.
    return MessageResponse(message="Sesión cerrada correctamente")

@router.get("/me", response_model=AdminResponse, status_code=status.HTTP_200_OK)
def me(current_admin: AdminResponse = Depends(get_current_admin)):
    return current_admin

# Endpoint para crear el primer admin (deshabilitar en producción o proteger con flag)
@router.post("/register", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
def register(data: CreateAdminRequest, db: Session = Depends(get_db)):
    return AuthService(db).create_admin(data)