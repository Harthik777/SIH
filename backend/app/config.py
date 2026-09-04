from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sentinel Investigation API"
    environment: str = "development"
    secret_key: str = "replace-this-secret-in-production"
    analyst_email: str = "analyst@sentinel.local"
    analyst_password: str = "sentinel-demo"
    database_url: str = "postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "sentinel-password"
    redis_url: str = "redis://localhost:6379/0"
    upload_dir: Path = Path(__file__).resolve().parent.parent / "data" / "uploads"
    max_upload_mb: int = 500
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SENTINEL_", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
