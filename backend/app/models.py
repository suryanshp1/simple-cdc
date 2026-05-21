"""
SimpleCDC — Pydantic domain models.

Shared request/response schemas for the REST API and WebSocket payloads.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CDCEvent(BaseModel):
    """Single Change-Data-Capture event row."""

    id: UUID
    table_name: str
    operation: str
    payload: dict
    created_at: datetime


class PaginatedEvents(BaseModel):
    """Paginated wrapper for event listings."""

    events: list[CDCEvent]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    """Liveness / readiness probe response."""

    status: str
    database: str
    websocket_clients: int
    timestamp: datetime


class TableInfo(BaseModel):
    """Per-table event statistics."""

    name: str
    event_count: int
