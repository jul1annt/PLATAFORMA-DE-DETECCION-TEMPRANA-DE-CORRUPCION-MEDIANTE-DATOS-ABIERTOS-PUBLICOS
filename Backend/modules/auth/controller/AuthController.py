from fastapi import APIRouter, Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.database import get_db
from modules.auth.service.AuthService import AuthService
from modules.auth.dto.request import LoginRequest, CreateAdminRequest
from modules.auth.dto.response import TokenResponse, AdminResponse, MessageResponse
from gateway.middlewares.auth_middleware import bearer_scheme, get_current_admin

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    return AuthService(db).login(data, client_ip=client_ip)

@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_admin: AdminResponse = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    AuthService(db).logout(credentials.credentials)
    return MessageResponse(message="Sesión cerrada correctamente")

@router.get("/me", response_model=AdminResponse, status_code=status.HTTP_200_OK)
def me(current_admin: AdminResponse = Depends(get_current_admin)):
    return current_admin

@router.post("/register", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: CreateAdminRequest,
    current_admin: AdminResponse = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AuthService(db).create_admin(data)
