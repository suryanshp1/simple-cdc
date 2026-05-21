"""
SimpleCDC — REST API routes.

Endpoints for CDC events, table statistics, health checks, and aggregate stats.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
import structlog

from app.api.auth import verify_token
from app.db import get_db_connection
from app.models import CDCEvent, HealthResponse, PaginatedEvents, TableInfo

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["events"])


# ---------------------------------------------------------------------------
# GET /api/events — paginated, filterable event list
# ---------------------------------------------------------------------------
@router.get("/events", response_model=PaginatedEvents)
async def list_events(
    request: Request,
    table_name: str | None = Query(default=None, description="Filter by table name"),
    operation: str | None = Query(default=None, description="Filter by operation (INSERT/UPDATE/DELETE)"),
    limit: int = Query(default=50, ge=1, le=500, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Offset"),
    _auth: bool = Depends(verify_token),
):
    """Return a paginated list of CDC events with optional filters."""
    conditions: list[str] = []
    params: list = []

    if table_name:
        conditions.append("table_name = %s")
        params.append(table_name)
    if operation:
        conditions.append("operation = %s")
        params.append(operation.upper())

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Total matching rows
            cur.execute(
                f"SELECT COUNT(*) AS cnt FROM cdc_events {where_clause}",
                params,
            )
            total = cur.fetchone()["cnt"]

            # Paginated results
            cur.execute(
                f"SELECT id, table_name, operation, payload, created_at "
                f"FROM cdc_events {where_clause} "
                f"ORDER BY created_at DESC LIMIT %s OFFSET %s",
                [*params, limit, offset],
            )
            rows = cur.fetchall()

    logger.info("events.listed", total=total, limit=limit, offset=offset)

    return PaginatedEvents(
        events=[CDCEvent(**row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# GET /api/events/{event_id} — single event by UUID
# ---------------------------------------------------------------------------
@router.get("/events/{event_id}", response_model=CDCEvent)
async def get_event(
    event_id: UUID,
    _auth: bool = Depends(verify_token),
):
    """Retrieve a single CDC event by its UUID."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, table_name, operation, payload, created_at "
                "FROM cdc_events WHERE id = %s",
                [str(event_id)],
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found",
        )

    logger.info("event.retrieved", event_id=str(event_id))
    return CDCEvent(**row)


# ---------------------------------------------------------------------------
# GET /api/tables — per-table event counts
# ---------------------------------------------------------------------------
@router.get("/tables", response_model=list[TableInfo])
async def list_tables(
    _auth: bool = Depends(verify_token),
):
    """Return distinct tables and their event counts, ordered desc."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name AS name, COUNT(*) AS event_count "
                "FROM cdc_events GROUP BY table_name "
                "ORDER BY event_count DESC"
            )
            rows = cur.fetchall()

    return [TableInfo(**row) for row in rows]


# ---------------------------------------------------------------------------
# GET /api/health — unauthenticated liveness probe
# ---------------------------------------------------------------------------
@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """Health-check endpoint — no authentication required."""
    db_status = "healthy"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        logger.error("health.db_fail", error=str(exc))
        db_status = "unhealthy"

    manager = getattr(request.app.state, "ws_manager", None)
    ws_clients = manager.client_count if manager else 0

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
        websocket_clients=ws_clients,
        timestamp=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# GET /api/stats — aggregate statistics
# ---------------------------------------------------------------------------
@router.get("/stats")
async def get_stats(
    _auth: bool = Depends(verify_token),
):
    """Return aggregate CDC statistics."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM cdc_events")
            total = cur.fetchone()["total"]

            cur.execute(
                "SELECT COUNT(*) AS recent FROM cdc_events "
                "WHERE created_at >= NOW() - INTERVAL '1 minute'"
            )
            recent = cur.fetchone()["recent"]

            cur.execute(
                "SELECT COUNT(DISTINCT table_name) AS tables FROM cdc_events"
            )
            tables = cur.fetchone()["tables"]

    return {
        "total_events": total,
        "events_last_minute": recent,
        "distinct_tables": tables,
    }
