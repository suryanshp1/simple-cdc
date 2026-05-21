"""
SimpleCDC — FastAPI application entrypoint.

Wires up:
  • CORS middleware
  • REST API router (``/api/*``)
  • WebSocket endpoint (``/ws``)
  • Background NOTIFY listener via lifespan context manager
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import settings
from app.api.events import router as events_router
from app.websocket.handler import (
    ConnectionManager,
    listen_for_notifications,
    websocket_endpoint,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown hooks
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Async lifespan context manager.

    On startup:
      1. Create a ``ConnectionManager`` and store it on ``app.state``.
      2. Spawn the PostgreSQL NOTIFY listener as a background asyncio task.

    On shutdown:
      1. Cancel the NOTIFY listener task.
    """
    manager = ConnectionManager()
    app.state.ws_manager = manager

    listener_task = asyncio.create_task(
        listen_for_notifications(manager, settings),
        name="notify-listener",
    )
    logger.info("app.startup", message="NOTIFY listener started")

    yield

    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass
    logger.info("app.shutdown", message="NOTIFY listener stopped")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SimpleCDC",
    version="1.0.0",
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REST routes ---
app.include_router(events_router)


# --- WebSocket route ---
@app.websocket("/ws")
async def ws_route(websocket: WebSocket, token: str = ""):
    """Proxy to the handler so we can inject app-level state."""
    manager: ConnectionManager = websocket.app.state.ws_manager
    await websocket_endpoint(websocket, token, manager, settings)


# --- Root ---
@app.get("/")
async def root():
    """Root endpoint — basic service identity."""
    return {"name": "SimpleCDC", "version": "1.0.0"}
