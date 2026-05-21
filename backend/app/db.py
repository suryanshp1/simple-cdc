"""
SimpleCDC — Database connection helper.

Provides a context-managed psycopg3 connection with dict_row factory.
"""

from contextlib import contextmanager
from typing import Generator

import psycopg
from psycopg.rows import dict_row
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


@contextmanager
def get_db_connection() -> Generator[psycopg.Connection, None, None]:
    """
    Yield a psycopg3 connection configured with ``dict_row`` factory.

    Usage::

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    conn = psycopg.connect(
        settings.database_url,
        row_factory=dict_row,
    )
    try:
        yield conn
    finally:
        conn.close()
