from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", Path(".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://banana:banana@localhost:5432/banana"
    embedding_dim: int = 1536
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 1440
    jwt_algorithm: str = "HS256"

    dify_base_url: str = "http://localhost/v1"
    dify_api_key: str = ""
    dify_wf_architecture: str = ""
    dify_wf_blueprint: str = ""
    dify_wf_chapter_draft: str = ""
    dify_wf_finalize_summary: str = ""
    dify_wf_consistency_review: str = ""

    job_timeout_sec: int = 600
    job_max_concurrency: int = 2

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
