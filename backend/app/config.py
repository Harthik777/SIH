from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sentinel Investigation API"
    environment: str = "development"
    secret_key: str = "replace-this-secret-in-production"
    analyst_email: str = "analyst@sentinel.local"
    analyst_password: str = "sentinel-demo"
    analyst_password_hash: str | None = None
    supervisor_email: str = "supervisor@sentinel.local"
    supervisor_password: str = "sentinel-supervisor"
    supervisor_password_hash: str | None = None
    auth_mode: Literal["optional", "required"] = "optional"
    token_ttl_minutes: int = 480
    database_url: str = "postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "sentinel-password"
    redis_url: str = "redis://localhost:6379/0"
    persistence_mode: Literal["local", "hybrid"] = "local"
    upload_dir: Path = Path(__file__).resolve().parent.parent / "data" / "uploads"
    investigation_dir: Path = Path(__file__).resolve().parent.parent / "data" / "investigations"
    audit_path: Path = Path(__file__).resolve().parent.parent / "data" / "investigations" / "audit_chain.jsonl"
    decisions_path: Path = Path(__file__).resolve().parent.parent / "data" / "investigations" / "suraksha_resolution_decisions.json"
    max_upload_mb: int = 500
    max_ingestion_records: int = 100_000
    max_ingestion_columns: int = 200
    max_cell_characters: int = 20_000
    rate_limit_per_minute: int = 600
    public_demo: bool = False
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SENTINEL_", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def production_secret_configured(self) -> bool:
        return len(self.secret_key) >= 32 and not self.secret_key.casefold().startswith("replace-")

    @property
    def private_credentials_configured(self) -> bool:
        def ready(password: str, encoded: str | None, default: str) -> bool:
            return bool(encoded) or (len(password) >= 12 and password != default and not password.casefold().startswith("replace-"))

        return ready(self.analyst_password, self.analyst_password_hash, "sentinel-demo") and ready(
            self.supervisor_password,
            self.supervisor_password_hash,
            "sentinel-supervisor",
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
