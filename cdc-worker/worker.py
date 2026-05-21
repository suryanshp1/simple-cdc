"""
SimpleCDC Worker — PostgreSQL WAL Change Data Capture.

Connects to PostgreSQL via logical replication (wal2json plugin),
polls the replication slot for WAL changes, persists each change
into the `cdc_events` table, and sends a NOTIFY so downstream
consumers (e.g. FastAPI WebSocket) can react in real-time.

Architecture notes:
  - Two separate connections: one for slot polling, one for writes.
    pg_logical_slot_get_changes holds an advisory lock on the slot for
    the duration of the transaction; a second connection avoids
    contention with the INSERT/NOTIFY path.
  - Both connections use autocommit=True so each statement is its own
    transaction — no long-running transactions that inflate WAL retention.
  - Exponential backoff on connection errors (1 → 2 → 4 … → 30 s).
  - Graceful shutdown on SIGTERM / SIGINT.
"""

from __future__ import annotations

import json
import signal
import sys
import time
import uuid
from typing import Any

import psycopg
import structlog

from config import Config

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

log: structlog.stdlib.BoundLogger = structlog.get_logger("cdc_worker")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKIP_TABLES = frozenset({"cdc_events"})

KIND_TO_OP = {
    "insert": "INSERT",
    "update": "UPDATE",
    "delete": "DELETE",
}

BACKOFF_BASE = 1.0     # seconds
BACKOFF_MAX = 30.0     # seconds
BACKOFF_FACTOR = 2.0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _connect(dsn: str) -> psycopg.Connection:
    """Open a psycopg3 connection with autocommit enabled."""
    conn = psycopg.connect(dsn, autocommit=True)
    log.info("database_connected", host=dsn.split("host=")[1].split(" ")[0])
    return conn


def _connect_with_retry(dsn: str, *, label: str = "db") -> psycopg.Connection:
    """Connect with exponential backoff — used at startup when PG may not be ready."""
    delay = BACKOFF_BASE
    while True:
        try:
            return _connect(dsn)
        except psycopg.OperationalError as exc:
            log.warning(
                "connection_failed",
                label=label,
                error=str(exc),
                retry_in=delay,
            )
            time.sleep(delay)
            delay = min(delay * BACKOFF_FACTOR, BACKOFF_MAX)


def _ensure_publication(cur: psycopg.Cursor, name: str) -> None:
    """Create the publication if it doesn't already exist."""
    try:
        cur.execute(
            psycopg.sql.SQL("CREATE PUBLICATION {} FOR ALL TABLES").format(
                psycopg.sql.Identifier(name)
            )
        )
        log.info("publication_created", publication=name)
    except psycopg.errors.DuplicateObject:
        log.info("publication_exists", publication=name)


def _ensure_replication_slot(cur: psycopg.Cursor, slot_name: str) -> None:
    """Create the logical replication slot (wal2json) if it doesn't exist."""
    try:
        cur.execute(
            "SELECT pg_create_logical_replication_slot(%s, %s)",
            (slot_name, "wal2json"),
        )
        log.info("replication_slot_created", slot=slot_name)
    except psycopg.errors.DuplicateObject:
        log.info("replication_slot_exists", slot=slot_name)


def _build_payload(change: dict[str, Any]) -> dict[str, Any]:
    """Construct the event payload from a wal2json change entry.

    - INSERT / UPDATE: zip columnnames → columnvalues
    - UPDATE with oldkeys: attach old key values
    - DELETE: use oldkeys as the payload
    """
    kind = change.get("kind", "")

    if kind == "delete":
        old = change.get("oldkeys", {})
        return dict(zip(old.get("keynames", []), old.get("keyvalues", [])))

    payload: dict[str, Any] = dict(
        zip(change.get("columnnames", []), change.get("columnvalues", []))
    )

    if kind == "update":
        old = change.get("oldkeys")
        if old:
            payload["__old_keys"] = dict(
                zip(old.get("keynames", []), old.get("keyvalues", []))
            )

    return payload


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


class CDCWorker:
    """Main CDC polling worker."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.running = True
        self._poll_conn: psycopg.Connection | None = None
        self._write_conn: psycopg.Connection | None = None

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        """Entry point — setup, loop, teardown."""
        self._register_signals()
        self._connect_all()
        self._bootstrap()
        log.info(
            "worker_started",
            slot=self.cfg.slot_name,
            publication=self.cfg.publication_name,
            poll_interval=self.cfg.poll_interval,
        )
        self._poll_loop()
        self._shutdown()

    def _register_signals(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum: int, _frame: Any) -> None:
        sig_name = signal.Signals(signum).name
        log.info("signal_received", signal=sig_name)
        self.running = False

    # -- connections ---------------------------------------------------------

    def _connect_all(self) -> None:
        dsn = self.cfg.database_url
        self._poll_conn = _connect_with_retry(dsn, label="poll")
        self._write_conn = _connect_with_retry(dsn, label="write")

    def _reconnect_all(self) -> None:
        """Tear down stale connections and reconnect."""
        for conn in (self._poll_conn, self._write_conn):
            try:
                if conn and not conn.closed:
                    conn.close()
            except Exception:
                pass
        self._connect_all()

    # -- bootstrap -----------------------------------------------------------

    def _bootstrap(self) -> None:
        """Create publication + replication slot if they don't exist."""
        assert self._poll_conn is not None
        with self._poll_conn.cursor() as cur:
            _ensure_publication(cur, self.cfg.publication_name)
            _ensure_replication_slot(cur, self.cfg.slot_name)

    # -- main loop -----------------------------------------------------------

    def _poll_loop(self) -> None:
        delay = BACKOFF_BASE

        while self.running:
            try:
                self._poll_once()
                delay = BACKOFF_BASE  # reset on success
                time.sleep(self.cfg.poll_interval)
            except (psycopg.OperationalError, psycopg.errors.AdminShutdown) as exc:
                if not self.running:
                    break
                log.error("connection_error", error=str(exc), retry_in=delay)
                time.sleep(delay)
                delay = min(delay * BACKOFF_FACTOR, BACKOFF_MAX)
                try:
                    self._reconnect_all()
                except Exception as re_exc:
                    log.error("reconnect_failed", error=str(re_exc))
            except Exception as exc:
                log.error("unexpected_error", error=str(exc), exc_info=True)
                if not self.running:
                    break
                time.sleep(delay)
                delay = min(delay * BACKOFF_FACTOR, BACKOFF_MAX)

    def _poll_once(self) -> None:
        """Fetch pending WAL changes and process them."""
        assert self._poll_conn is not None
        assert self._write_conn is not None

        with self._poll_conn.cursor() as cur:
            cur.execute(
                "SELECT lsn, xid, data "
                "FROM pg_logical_slot_get_changes(%s, NULL, NULL)",
                (self.cfg.slot_name,),
            )
            rows = cur.fetchall()

        if not rows:
            return

        for lsn, xid, data in rows:
            self._process_wal_message(lsn, xid, data)

    def _process_wal_message(
        self, lsn: str, xid: int, raw_data: str
    ) -> None:
        """Parse a single wal2json message and persist each change."""
        try:
            message = json.loads(raw_data)
        except json.JSONDecodeError:
            log.error("wal_json_parse_error", lsn=lsn, data=raw_data[:200])
            return

        changes: list[dict[str, Any]] = message.get("change", [])

        for change in changes:
            table = change.get("table", "")
            schema = change.get("schema", "public")

            if table in SKIP_TABLES:
                continue

            kind = change.get("kind", "")
            operation = KIND_TO_OP.get(kind)
            if operation is None:
                log.warning("unknown_change_kind", kind=kind, lsn=lsn)
                continue

            event_id = str(uuid.uuid4())
            payload = _build_payload(change)

            self._persist_event(event_id, table, operation, payload)

            log.info(
                "event_captured",
                event_id=event_id,
                schema=schema,
                table=table,
                operation=operation,
                lsn=lsn,
                xid=xid,
            )

    def _persist_event(
        self,
        event_id: str,
        table: str,
        operation: str,
        payload: dict[str, Any],
    ) -> None:
        """INSERT into cdc_events and NOTIFY listeners."""
        assert self._write_conn is not None

        with self._write_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO cdc_events (id, table_name, operation, payload, created_at) "
                "VALUES (%s, %s, %s, %s::jsonb, NOW())",
                (event_id, table, operation, json.dumps(payload)),
            )
            cur.execute(
                psycopg.sql.SQL("NOTIFY cdc_events_channel, {}").format(
                    psycopg.sql.Literal(event_id)
                )
            )

    # -- shutdown ------------------------------------------------------------

    def _shutdown(self) -> None:
        log.info("worker_shutting_down")
        for label, conn in [("poll", self._poll_conn), ("write", self._write_conn)]:
            try:
                if conn and not conn.closed:
                    conn.close()
                    log.info("connection_closed", label=label)
            except Exception as exc:
                log.error("connection_close_error", label=label, error=str(exc))
        log.info("worker_stopped")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    cfg = Config.from_env()
    log.info(
        "config_loaded",
        db_host=cfg.db_host,
        db_port=cfg.db_port,
        db_name=cfg.db_name,
        slot=cfg.slot_name,
        publication=cfg.publication_name,
    )
    worker = CDCWorker(cfg)
    worker.start()


if __name__ == "__main__":
    main()
