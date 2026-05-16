from datetime import datetime, timedelta
from jose import JWTError, jwt
# pyrefly: ignore [missing-import]
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from modules.auth.config.settings import settings
from modules.auth.model.Admin import Admin
from modules.auth.repository.AuthRepository import AuthRepository
from modules.auth.dto.request import LoginRequest, CreateAdminRequest
from modules.auth.dto.response import TokenResponse, AdminResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: Session):
        self.repository = AuthRepository(db)

    # ── Utilidades de contraseña ──────────────────────────────────────────

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    # ── Utilidades de JWT ─────────────────────────────────────────────────

    def create_access_token(self, admin_id: int, username: str) -> str:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {
            "sub": str(admin_id),
            "username": username,
            "exp": expire,
            "type": "admin",
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def decode_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            if payload.get("type") != "admin":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
                )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # ── Casos de uso ──────────────────────────────────────────────────────

    def login(self, data: LoginRequest) -> TokenResponse:
        admin = self.repository.get_by_username(data.username)

        if not admin or not self.verify_password(data.password, admin.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
            )

        token = self.create_access_token(admin.id, admin.username)

        return TokenResponse(
            access_token=token, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    def create_admin(self, data: CreateAdminRequest) -> AdminResponse:
        existing = self.repository.get_by_username(data.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="El usuario ya existe"
            )

        new_admin = Admin(
            username=data.username,
            email=data.email,
            hashed_password=self.hash_password(data.password),
        )
        created = self.repository.create(new_admin)
        return AdminResponse.model_validate(created)

    def get_current_admin(self, token: str) -> AdminResponse:
        payload = self.decode_token(token)
        admin = self.repository.get_by_id(int(payload["sub"]))
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Administrador no encontrado",
            )
        return AdminResponse.model_validate(admin)
