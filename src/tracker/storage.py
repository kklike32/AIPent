from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .events import Event, EventType


class SQLiteStorage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    stopped_at TEXT,
                    status TEXT NOT NULL,
                    local_only_mode INTEGER NOT NULL DEFAULT 1,
                    screenshot_interval_seconds INTEGER NOT NULL,
                    ocr_enabled INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    app_name TEXT,
                    window_title TEXT,
                    metadata TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )

    def create_session(
        self,
        *,
        local_only_mode: bool,
        screenshot_interval_seconds: int,
        ocr_enabled: bool,
    ) -> int:
        started_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (started_at, status, local_only_mode, screenshot_interval_seconds, ocr_enabled)
                VALUES (?, 'running', ?, ?, ?)
                """,
                (
                    started_at,
                    int(local_only_mode),
                    screenshot_interval_seconds,
                    int(ocr_enabled),
                ),
            )
            return int(cursor.lastrowid)

    def stop_session(self, session_id: int) -> None:
        stopped_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET stopped_at = ?, status = 'stopped'
                WHERE id = ?
                """,
                (stopped_at, session_id),
            )

    def set_session_status(self, session_id: int, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET status = ? WHERE id = ?",
                (status, session_id),
            )

    def get_latest_session_id(self) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM sessions ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return int(row["id"]) if row else None

    def get_active_session_id(self) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM sessions WHERE status = 'running' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return int(row["id"]) if row else None

    def add_event(self, event: Event) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (session_id, timestamp, event_type, app_name, window_title, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.session_id,
                    event.iso_timestamp(),
                    event.event_type.value,
                    event.app_name,
                    event.window_title,
                    json.dumps(event.metadata),
                ),
            )
            event_id = int(cursor.lastrowid)
            event.id = event_id
            return event_id

    def get_events(self, session_id: int) -> list[Event]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, timestamp, event_type, app_name, window_title, metadata
                FROM events
                WHERE session_id = ?
                ORDER BY timestamp ASC, id ASC
                """,
                (session_id,),
            ).fetchall()

        events: list[Event] = []
        for row in rows:
            events.append(
                Event(
                    id=int(row["id"]),
                    session_id=int(row["session_id"]),
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    event_type=EventType(row["event_type"]),
                    app_name=row["app_name"],
                    window_title=row["window_title"],
                    metadata=json.loads(row["metadata"]),
                )
            )
        return events
