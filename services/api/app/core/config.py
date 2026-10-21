from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

API_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=API_ENV_FILE, env_file_encoding="utf-8")

    # ASSUMPTION: This local development URL follows tech.md; deployments must set DATABASE_URL.
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/dmp"


@lru_cache
def get_settings() -> Settings:
    return Settings()
