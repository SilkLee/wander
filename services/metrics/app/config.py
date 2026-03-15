from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8005
    database_url: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_prefix": "", "case_sensitive": False}
