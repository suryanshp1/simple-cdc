"""
CDC Worker Configuration.

Reads all settings from environment variables with sensible defaults
for local Docker Compose development. Uses a frozen dataclass so config
is immutable after construction.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Config:
    """Immutable configuration for the CDC worker."""

    db_host: str = "postgres"
    db_port: int = 5432
    db_user: str = "admin"
    db_password: str = "admin"
    db_name: str = "app"
    slot_name: str = "simplecdc_slot"
    publication_name: str = "simplecdc_pub"
    poll_interval: float = 0.1  # seconds

    @property
    def database_url(self) -> str:
        """Construct a PostgreSQL connection string (libpq key=value format)."""
        return (
            f"host={self.db_host} "
            f"port={self.db_port} "
            f"dbname={self.db_name} "
            f"user={self.db_user} "
            f"password={self.db_password}"
        )

    @classmethod
    def from_env(cls) -> Config:
        """Build a Config instance from environment variables.

        Environment variables use UPPER_SNAKE_CASE names matching the
        field names (e.g. DB_HOST, POLL_INTERVAL).
        """
        return cls(
            db_host=os.getenv("DB_HOST", "postgres"),
            db_port=int(os.getenv("DB_PORT", "5432")),
            db_user=os.getenv("DB_USER", "admin"),
            db_password=os.getenv("DB_PASSWORD", "admin"),
            db_name=os.getenv("DB_NAME", "app"),
            slot_name=os.getenv("SLOT_NAME", "simplecdc_slot"),
            publication_name=os.getenv("PUBLICATION_NAME", "simplecdc_pub"),
            poll_interval=float(os.getenv("POLL_INTERVAL", "0.1")),
        )
