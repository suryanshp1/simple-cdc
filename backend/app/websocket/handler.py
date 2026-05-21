"""
SimpleCDC — WebSocket connection manager and PostgreSQL NOTIFY listener.

Handles:
  1. WebSocket lifecycle (connect / disconnect / broadcast)
  2. Background async listener on ``cdc_events_channel`` that pushes
     new CDC events to all connected WebSocket clients in real-time.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
import psycopg
from psycopg.rows import dict_row
import structlog

from app.config import Settings

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Connection Manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    """Manages active WebSocket connections and fan-out broadcasts."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("ws.connected", clients=self.client_count)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket client from the active list."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("ws.disconnected", clients=self.client_count)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """
        Send *message* as JSON to every connected client.

        Individual send failures are caught so one broken client
        cannot disrupt the rest.
        """
        stale: list[WebSocket] = []
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception as exc:
                logger.warning("ws.broadcast_error", error=str(exc))
                stale.append(ws)

        # Clean up dead connections discovered during broadcast
        for ws in stale:
            self.disconnect(ws)

    @property
    def client_count(self) -> int:
        return len(self.active_connections)


# ---------------------------------------------------------------------------
# WebSocket endpoint handler
# ---------------------------------------------------------------------------
async def websocket_endpoint(websocket: WebSocket, token: str, manager: ConnectionManager, settings: Settings) -> None:
    """
    WebSocket endpoint at ``/ws``.

    Query param ``token`` is validated against the configured API_TOKEN.
    On success the client receives a welcome frame and the connection is
    kept alive until the client disconnects.
    """
    # --- Auth ---
    if token != settings.API_TOKEN:
        await websocket.close(code=4001, reason="Invalid token")
        logger.warning("ws.auth_failed")
        return

    await manager.connect(websocket)

    try:
        # Welcome handshake
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to SimpleCDC",
        })

        # Keep-alive loop — we don't expect meaningful inbound messages
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error("ws.error", error=str(exc))
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# PostgreSQL NOTIFY listener (async background task)
# ---------------------------------------------------------------------------
async def listen_for_notifications(manager: ConnectionManager, settings: Settings) -> None:
    """
    Long-running async task that LISTENs on ``cdc_events_channel``.

    For each NOTIFY payload (an event UUID), the full event row is fetched
    via a persistent query connection and broadcast to all WebSocket clients.

    Reconnects automatically on connection loss with exponential back-off
    capped at 30 seconds.
    """
    backoff = 1  # seconds

    while True:
        query_conn: psycopg.AsyncConnection | None = None
        try:
            # LISTEN connection — stays open for NOTIFY events
            async with await psycopg.AsyncConnection.connect(
                settings.database_url,
                autocommit=True,
            ) as listen_conn:
                # Persistent query connection — reused across notifications
                query_conn = await psycopg.AsyncConnection.connect(
                    settings.database_url,
                    autocommit=True,
                    row_factory=dict_row,
                )

                await listen_conn.execute("LISTEN cdc_events_channel")
                logger.info("notify.listening", channel="cdc_events_channel")
                backoff = 1  # reset on successful connect

                async for notify in listen_conn.notifies():
                    event_id = notify.payload
                    logger.debug("notify.received", event_id=event_id)

                    try:
                        async with query_conn.cursor() as cur:
                            await cur.execute(
                                "SELECT id, table_name, operation, payload, created_at "
                                "FROM cdc_events WHERE id = %s",
                                [event_id],
                            )
                            row = await cur.fetchone()

                        if row is not None:
                            event_data = {
                                "id": str(row["id"]),
                                "table_name": row["table_name"],
                                "operation": row["operation"],
                                "payload": row["payload"],
                                "created_at": row["created_at"].isoformat()
                                if isinstance(row["created_at"], datetime)
                                else str(row["created_at"]),
                            }
                            await manager.broadcast({
                                "type": "cdc_event",
                                "data": event_data,
                            })
                        else:
                            logger.warning("notify.event_not_found", event_id=event_id)

                    except Exception as exc:
                        logger.error("notify.fetch_error", event_id=event_id, error=str(exc))

        except asyncio.CancelledError:
            logger.info("notify.cancelled")
            raise  # let the task terminate cleanly
        except Exception as exc:
            logger.error("notify.connection_error", error=str(exc), retry_in=backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
        finally:
            if query_conn is not None:
                try:
                    await query_conn.close()
                except Exception:
                    pass
