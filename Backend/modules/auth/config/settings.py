from pydantic_settings import BaseSettings

from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: Optional[str] = None
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hora por defecto

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()