"""
SimpleCDC — Application configuration via pydantic-settings.

Loads from environment variables with .env file fallback.
"""

from pydantic_settings import BaseSettings
from pydantic import model_validator


class Settings(BaseSettings):
    """Central configuration loaded from env vars / .env file."""

    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    DB_USER: str = "admin"
    DB_PASSWORD: str = "admin"
    DB_NAME: str = "app"
    API_TOKEN: str = "changeme"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    @property
    def database_url(self) -> str:
        """Construct the PostgreSQL connection DSN."""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
