from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    ENCRYPTION_KEY: str
    MAX_SYNC_RETRIES: int = 3
    SYNC_RETRY_DELAY_SECONDS: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
