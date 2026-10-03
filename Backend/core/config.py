from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing import Annotated
from cryptography.fernet import Fernet
from urllib.parse import urlsplit


def normalize_cors_origins(origins: list[str]) -> list[str]:
    """Require explicit HTTP(S) origins for cross-origin browser access."""
    normalized = []
    for value in origins:
        origin = value.strip()
        parsed = urlsplit(origin)
        try:
            port = parsed.port
        except ValueError as exc:
            raise ValueError("CORS_ORIGINS contiene un puerto inválido") from exc
        if (
            origin == "*"
            or parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("CORS_ORIGINS debe contener orígenes HTTP(S) exactos, sin rutas ni comodines")
        host = parsed.hostname.lower()
        if ":" in host:  # Preserve brackets around IPv6 literals in the authority.
            host = f"[{host}]"
        if port is not None and not (
            (parsed.scheme == "http" and port == 80)
            or (parsed.scheme == "https" and port == 443)
        ):
            host = f"{host}:{port}"
        normalized.append(f"{parsed.scheme}://{host}")
    if not normalized:
        raise ValueError("CORS_ORIGINS debe declarar al menos un origen permitido")
    return list(dict.fromkeys(normalized))

class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    ENCRYPTION_KEY: str
    ENCRYPTION_KEY_PREVIOUS: str | None = None
    SECRET_KEY: str
    SCHEDULER_TIMEZONE: str = "America/Bogota"
    CORS_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    INGESTA_ALLOWED_HOSTS: Annotated[list[str], NoDecode] = ["www.datos.gov.co", "datos.gov.co"]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_MINUTES: int = 15
    INGESTA_OVERLAP_HOURS: int = 48
    INGESTA_MAX_RECORDS_PER_SYNC: int = 100000
    EXPORT_ARTIFACT_DIR: str = "var/exports"
    EXPORT_MAX_ROWS: int = 50000
    EXPORT_CAPABILITY_TTL_HOURS: int = 24
    EXPORT_ARTIFACT_TTL_HOURS: int = 24

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @field_validator("CORS_ORIGINS", "INGESTA_ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_csv_list(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, value: list[str]) -> list[str]:
        return normalize_cors_origins(value)

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32 or value.startswith(("cambia_", "pega_")):
            raise ValueError("SECRET_KEY debe ser una clave aleatoria de al menos 32 caracteres")
        return value

    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, value: str) -> str:
        try:
            Fernet(value.encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise ValueError("ENCRYPTION_KEY debe ser una clave Fernet válida") from exc
        return value

    @field_validator("ENCRYPTION_KEY_PREVIOUS")
    @classmethod
    def validate_previous_encryption_key(cls, value: str | None) -> str | None:
        if value:
            try:
                Fernet(value.encode("utf-8"))
            except (TypeError, ValueError) as exc:
                raise ValueError("ENCRYPTION_KEY_PREVIOUS debe ser una clave Fernet válida") from exc
        return value

    @field_validator(
        "LOGIN_MAX_ATTEMPTS",
        "LOGIN_WINDOW_MINUTES",
        "INGESTA_OVERLAP_HOURS",
        "INGESTA_MAX_RECORDS_PER_SYNC",
        "EXPORT_MAX_ROWS",
        "EXPORT_CAPABILITY_TTL_HOURS",
        "EXPORT_ARTIFACT_TTL_HOURS",
    )
    @classmethod
    def validate_positive_policy_limits(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Los límites de operación deben ser mayores que cero")
        return value

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

settings = Settings()
