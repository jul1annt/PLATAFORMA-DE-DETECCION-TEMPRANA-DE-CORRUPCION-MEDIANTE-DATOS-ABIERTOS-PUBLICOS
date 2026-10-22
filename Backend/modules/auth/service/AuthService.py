from datetime import datetime, timedelta, timezone
import hashlib
import uuid
import jwt
from jwt import InvalidTokenError
# pyrefly: ignore [missing-import]
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from shared.errors import AuthError

from core.config import settings
from modules.auth.config.settings import ALGORITHM
from modules.auth.model.Admin import Admin
from modules.auth.model.AdminSession import AdminSession
from modules.auth.repository.AuthRepository import AuthRepository
from modules.auth.dto.request import LoginRequest, CreateAdminRequest, validate_password_text
from modules.auth.dto.response import TokenResponse, AdminResponse

pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: Session):
        self.repository = AuthRepository(db)

    # ── Utilidades de contraseña ──────────────────────────────────────────

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    # ── Utilidades de JWT ─────────────────────────────────────────────────

    def create_access_token(self, admin_id: int, username: str) -> tuple[str, str, datetime]:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        jti = str(uuid.uuid4())
        payload = {
            "sub": str(admin_id),
            "username": username,
            "exp": expire,
            "type": "admin",
            "jti": jti,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM), jti, expire

    def decode_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"require": ["exp", "sub", "jti", "type"]},
            )
            if payload.get("type") != "admin" or not payload.get("sub") or not payload.get("jti"):
                raise AuthError("invalid_token", "Token inválido")
            int(payload["sub"])
            return payload
        except (InvalidTokenError, TypeError, ValueError):
            raise AuthError("expired_token", "Token inválido o expirado")

    # ── Casos de uso ──────────────────────────────────────────────────────

    def _login_key(self, username: str, client_ip: str) -> str:
        value = f"{username.strip().lower()}|{client_ip}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def login(self, data: LoginRequest, client_ip: str = "unknown") -> TokenResponse:
        try:
            validate_password_text(data.password, minimum=8)
        except ValueError as exc:
            raise AuthError("malformed_password", str(exc)) from exc
        login_key = self._login_key(data.username, client_ip)
        # Hold a transaction-scoped PostgreSQL advisory lock until this
        # request either records a failure or clears failures on success.
        # This keeps simultaneous requests from all observing the same count.
        self.repository.lock_login_attempts(login_key)
        since = datetime.now(timezone.utc) - timedelta(minutes=settings.LOGIN_WINDOW_MINUTES)
        if self.repository.count_recent_failures(login_key, since) >= settings.LOGIN_MAX_ATTEMPTS:
            raise AuthError("rate_limited", "Demasiados intentos. Intenta nuevamente más tarde.")

        admin = self.repository.get_by_username(data.username)

        if not admin or not self.verify_password(data.password, admin.hashed_password):
            self.repository.record_failure(login_key)
            raise AuthError("bad_credentials", "Credenciales incorrectas")

        self.repository.clear_failures(login_key)
        token, jti, expires_at = self.create_access_token(admin.id, admin.username)
        self.repository.create_session(AdminSession(
            jti=jti,
            admin_id=admin.id,
            expires_at=expires_at,
        ))

        return TokenResponse(
            access_token=token, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    def create_admin(self, data: CreateAdminRequest) -> AdminResponse:
        try:
            validate_password_text(data.password, minimum=12)
        except ValueError as exc:
            raise AuthError("malformed_password", str(exc)) from exc

        existing = self.repository.get_by_username(data.username, active_only=False)
        if existing:
            raise AuthError("duplicate_username", "El usuario ya existe")
        if self.repository.get_by_email(data.email):
            raise AuthError("duplicate_email", "El correo ya está registrado")

        new_admin = Admin(
            username=data.username,
            email=data.email,
            hashed_password=self.hash_password(data.password),
        )
        try:
            created = self.repository.create(new_admin)
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise AuthError("duplicate_admin", "El usuario o correo ya está registrado") from exc
        return AdminResponse.model_validate(created)

    def get_current_admin(self, token: str) -> AdminResponse:
        payload = self.decode_token(token)
        now = datetime.now(timezone.utc)
        if not self.repository.get_active_session(payload["jti"], now):
            raise AuthError("session_invalid", "Sesión revocada o expirada")
        admin = self.repository.get_by_id(int(payload["sub"]), active_only=True)
        if not admin:
            raise AuthError("admin_missing", "Administrador no encontrado")
        return AdminResponse.model_validate(admin)

    def logout(self, token: str) -> None:
        payload = self.decode_token(token)
        self.repository.revoke_session(payload["jti"], datetime.now(timezone.utc))
