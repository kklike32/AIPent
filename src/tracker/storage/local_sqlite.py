from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from tracker.events import (
    AgentHandoffDraft,
    ChunkSummary,
    Event,
    EventType,
    FinalPseudocode,
    ScreenshotRecord,
    Session,
    WorkflowInsight,
    WorkflowSearchIndexRecord,
    WorkflowTemplate,
)
from tracker.storage.repository import TrackerRepository


class LocalSQLiteRepository(TrackerRepository):
    PURGEABLE_EVENT_TYPES = (
        EventType.MOUSE_CLICK.value,
        EventType.KEYBOARD_KEY.value,
        EventType.KEYBOARD_SHORTCUT.value,
        EventType.ACTIVE_WINDOW.value,
        EventType.SCREENSHOT.value,
        EventType.OCR_TEXT.value,
        EventType.AUDIO_RECORDING.value,
    )

    def __init__(self, db_path: Path):
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
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    visibility TEXT NOT NULL DEFAULT 'private',
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    session_name TEXT,
                    device_name TEXT,
                    os_name TEXT,
                    sync_enabled INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    cloud_id TEXT,
                    synced INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    app_name TEXT,
                    window_title TEXT,
                    metadata TEXT NOT NULL,
                    synced INTEGER NOT NULL DEFAULT 0,
                    cloud_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS screenshots (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    event_id TEXT,
                    local_path TEXT NOT NULL,
                    storage_path TEXT,
                    ocr_text TEXT,
                    captured_at TEXT NOT NULL,
                    synced INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id),
                    FOREIGN KEY(event_id) REFERENCES events(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunk_summaries (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    chunk_index INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    observed_apps TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    synced INTEGER NOT NULL DEFAULT 0,
                    cloud_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS final_pseudocode (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    pseudocode TEXT NOT NULL,
                    plain_text TEXT NOT NULL,
                    suggestions TEXT NOT NULL,
                    synced INTEGER NOT NULL DEFAULT 0,
                    cloud_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_insights (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    summary TEXT NOT NULL,
                    main_apps TEXT NOT NULL,
                    detected_task_type TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    automation_score INTEGER NOT NULL,
                    automation_reason TEXT NOT NULL,
                    recommended_next_action TEXT NOT NULL,
                    synced INTEGER NOT NULL DEFAULT 0,
                    cloud_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_templates (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    tags TEXT NOT NULL,
                    pseudocode TEXT NOT NULL,
                    plain_text TEXT NOT NULL,
                    visibility TEXT NOT NULL DEFAULT 'private',
                    shared_with_team INTEGER NOT NULL DEFAULT 0,
                    created_from TEXT NOT NULL DEFAULT 'session_summary',
                    synced INTEGER NOT NULL DEFAULT 0,
                    cloud_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_handoff_queue (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    template_id TEXT,
                    status TEXT NOT NULL,
                    proposed_action TEXT NOT NULL,
                    action_plan TEXT NOT NULL,
                    requires_user_approval INTEGER NOT NULL DEFAULT 1,
                    approved_at TEXT,
                    executed_at TEXT,
                    synced INTEGER NOT NULL DEFAULT 0,
                    cloud_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id),
                    FOREIGN KEY(template_id) REFERENCES workflow_templates(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_search_index (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    template_id TEXT,
                    searchable_text TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    visibility TEXT NOT NULL DEFAULT 'private',
                    synced INTEGER NOT NULL DEFAULT 0,
                    cloud_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id),
                    FOREIGN KEY(template_id) REFERENCES workflow_templates(id)
                )
                """
            )
            self._add_column_if_missing(conn, "sessions", "visibility", "TEXT NOT NULL DEFAULT 'private'")
            self._add_column_if_missing(conn, "chunk_summaries", "user_id", "TEXT")
            self._add_column_if_missing(conn, "final_pseudocode", "user_id", "TEXT")
            self._add_column_if_missing(conn, "workflow_insights", "user_id", "TEXT")
            self._add_column_if_missing(conn, "workflow_templates", "user_id", "TEXT")
            self._add_column_if_missing(
                conn,
                "workflow_templates",
                "visibility",
                "TEXT NOT NULL DEFAULT 'private'",
            )
            self._add_column_if_missing(
                conn,
                "workflow_templates",
                "shared_with_team",
                "INTEGER NOT NULL DEFAULT 0",
            )
            self._add_column_if_missing(conn, "agent_handoff_queue", "user_id", "TEXT")
            self._add_column_if_missing(conn, "workflow_search_index", "user_id", "TEXT")
            self._add_column_if_missing(
                conn,
                "workflow_search_index",
                "visibility",
                "TEXT NOT NULL DEFAULT 'private'",
            )

    def _add_column_if_missing(
        self,
        conn: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if any(row[1] == column for row in rows):
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def create_session(self, session: Session) -> Session:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    id, user_id, visibility, started_at, ended_at, session_name, device_name, os_name,
                    sync_enabled, status, cloud_id, synced, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.user_id,
                    session.visibility,
                    session.started_at.isoformat(),
                    session.ended_at.isoformat() if session.ended_at else None,
                    session.session_name,
                    session.device_name,
                    session.os_name,
                    int(session.sync_enabled),
                    session.status,
                    session.cloud_id,
                    int(session.synced),
                    session.created_at.isoformat(),
                ),
            )
        return session

    def update_session(self, session: Session) -> Session:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET user_id = ?, visibility = ?, started_at = ?, ended_at = ?, session_name = ?, device_name = ?,
                    os_name = ?, sync_enabled = ?, status = ?, cloud_id = ?, synced = ?
                WHERE id = ?
                """,
                (
                    session.user_id,
                    session.visibility,
                    session.started_at.isoformat(),
                    session.ended_at.isoformat() if session.ended_at else None,
                    session.session_name,
                    session.device_name,
                    session.os_name,
                    int(session.sync_enabled),
                    session.status,
                    session.cloud_id,
                    int(session.synced),
                    session.id,
                ),
            )
        return session

    def save_event(self, event: Event) -> Event:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO events (
                    id, session_id, timestamp, event_type, app_name, window_title,
                    metadata, synced, cloud_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.session_id,
                    event.timestamp.isoformat(),
                    event.event_type.value,
                    event.app_name,
                    event.window_title,
                    json.dumps(event.metadata),
                    int(event.synced),
                    event.cloud_id,
                    event.created_at.isoformat(),
                ),
            )
        return event

    def save_screenshot(self, screenshot: ScreenshotRecord) -> ScreenshotRecord:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO screenshots (
                    id, session_id, event_id, local_path, storage_path, ocr_text,
                    captured_at, synced, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    screenshot.id,
                    screenshot.session_id,
                    screenshot.event_id,
                    screenshot.local_path,
                    screenshot.storage_path,
                    screenshot.ocr_text,
                    screenshot.captured_at.isoformat(),
                    int(screenshot.synced),
                    screenshot.created_at.isoformat(),
                ),
            )
        return screenshot

    def save_chunk_summary(self, summary: ChunkSummary) -> ChunkSummary:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO chunk_summaries (
                    id, session_id, user_id, chunk_index, started_at, ended_at, summary,
                    observed_apps, confidence, synced, cloud_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary.id,
                    summary.session_id,
                    summary.user_id,
                    summary.chunk_index,
                    summary.started_at,
                    summary.ended_at,
                    summary.summary,
                    json.dumps(summary.observed_apps),
                    summary.confidence,
                    int(summary.synced),
                    summary.cloud_id,
                    summary.created_at.isoformat(),
                ),
            )
        return summary

    def save_final_pseudocode(self, final: FinalPseudocode) -> FinalPseudocode:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO final_pseudocode (
                    id, session_id, user_id, pseudocode, plain_text, suggestions,
                    synced, cloud_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    final.id,
                    final.session_id,
                    final.user_id,
                    json.dumps(final.pseudocode),
                    final.plain_text,
                    json.dumps(final.suggestions),
                    int(final.synced),
                    final.cloud_id,
                    final.created_at.isoformat(),
                ),
            )
        return final

    def save_workflow_insight(self, insight: WorkflowInsight) -> WorkflowInsight:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO workflow_insights (
                    id, session_id, user_id, summary, main_apps, detected_task_type, tags,
                    automation_score, automation_reason, recommended_next_action,
                    synced, cloud_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    insight.id,
                    insight.session_id,
                    insight.user_id,
                    insight.summary,
                    json.dumps(insight.main_apps),
                    insight.detected_task_type,
                    json.dumps(insight.tags),
                    insight.automation_score,
                    insight.automation_reason,
                    insight.recommended_next_action,
                    int(insight.synced),
                    insight.cloud_id,
                    insight.created_at.isoformat(),
                ),
            )
        return insight

    def save_workflow_template(self, template: WorkflowTemplate) -> WorkflowTemplate:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO workflow_templates (
                    id, session_id, user_id, title, description, category, tags, pseudocode,
                    plain_text, visibility, shared_with_team, created_from, synced, cloud_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template.id,
                    template.session_id,
                    template.user_id,
                    template.title,
                    template.description,
                    template.category,
                    json.dumps(template.tags),
                    json.dumps(template.pseudocode),
                    template.plain_text,
                    template.visibility,
                    int(template.shared_with_team),
                    template.created_from,
                    int(template.synced),
                    template.cloud_id,
                    template.created_at.isoformat(),
                ),
            )
        return template

    def save_agent_handoff_draft(self, draft: AgentHandoffDraft) -> AgentHandoffDraft:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_handoff_queue (
                    id, session_id, user_id, template_id, status, proposed_action, action_plan,
                    requires_user_approval, approved_at, executed_at,
                    synced, cloud_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft.id,
                    draft.session_id,
                    draft.user_id,
                    draft.template_id,
                    draft.status,
                    draft.proposed_action,
                    json.dumps(draft.action_plan),
                    int(draft.requires_user_approval),
                    draft.approved_at.isoformat() if draft.approved_at else None,
                    draft.executed_at.isoformat() if draft.executed_at else None,
                    int(draft.synced),
                    draft.cloud_id,
                    draft.created_at.isoformat(),
                ),
            )
        return draft

    def save_workflow_search_index(
        self,
        record: WorkflowSearchIndexRecord,
    ) -> WorkflowSearchIndexRecord:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO workflow_search_index (
                    id, session_id, user_id, template_id, searchable_text, tags, visibility,
                    synced, cloud_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.session_id,
                    record.user_id,
                    record.template_id,
                    record.searchable_text,
                    json.dumps(record.tags),
                    record.visibility,
                    int(record.synced),
                    record.cloud_id,
                    record.created_at.isoformat(),
                ),
            )
        return record

    def get_latest_session(self) -> Session | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
        return self._row_to_session(row) if row else None

    def get_active_session(self) -> Session | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE status = 'running' ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
        return self._row_to_session(row) if row else None

    def get_session(self, session_id: str) -> Session | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return self._row_to_session(row) if row else None

    def get_events(self, session_id: str) -> list[Event]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def get_screenshots(self, session_id: str) -> list[ScreenshotRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM screenshots WHERE session_id = ? ORDER BY captured_at ASC",
                (session_id,),
            ).fetchall()
        return [self._row_to_screenshot(row) for row in rows]

    def get_chunk_summaries(self, session_id: str) -> list[ChunkSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chunk_summaries WHERE session_id = ? ORDER BY chunk_index ASC",
                (session_id,),
            ).fetchall()
        return [self._row_to_chunk_summary(row) for row in rows]

    def get_final_pseudocode(self, session_id: str) -> FinalPseudocode | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM final_pseudocode
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        return self._row_to_final_pseudocode(row) if row else None

    def get_workflow_insight(self, session_id: str) -> WorkflowInsight | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM workflow_insights
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        return self._row_to_workflow_insight(row) if row else None

    def get_workflow_template(self, template_id: str) -> WorkflowTemplate | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workflow_templates WHERE id = ?",
                (template_id,),
            ).fetchone()
        return self._row_to_workflow_template(row) if row else None

    def get_latest_workflow_template_for_session(self, session_id: str) -> WorkflowTemplate | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM workflow_templates
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        return self._row_to_workflow_template(row) if row else None

    def get_agent_handoff_draft(self, session_id: str) -> AgentHandoffDraft | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM agent_handoff_queue
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        return self._row_to_agent_handoff_draft(row) if row else None

    def get_workflow_search_index_record(self, session_id: str) -> WorkflowSearchIndexRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM workflow_search_index
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        return self._row_to_workflow_search_index_record(row) if row else None

    def list_unsynced_sessions(self) -> list[Session]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM sessions WHERE synced = 0").fetchall()
        return [self._row_to_session(row) for row in rows]

    def list_unsynced_chunk_summaries(self, session_id: str | None = None) -> list[ChunkSummary]:
        query = "SELECT * FROM chunk_summaries WHERE synced = 0"
        params: tuple[object, ...] = ()
        if session_id:
            query += " AND session_id = ?"
            params = (session_id,)
        query += " ORDER BY chunk_index ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_chunk_summary(row) for row in rows]

    def list_unsynced_final_pseudocode(
        self,
        session_id: str | None = None,
    ) -> list[FinalPseudocode]:
        query = "SELECT * FROM final_pseudocode WHERE synced = 0"
        params: tuple[object, ...] = ()
        if session_id:
            query += " AND session_id = ?"
            params = (session_id,)
        query += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_final_pseudocode(row) for row in rows]

    def list_unsynced_workflow_insights(
        self,
        session_id: str | None = None,
    ) -> list[WorkflowInsight]:
        query = "SELECT * FROM workflow_insights WHERE synced = 0"
        params: tuple[object, ...] = ()
        if session_id:
            query += " AND session_id = ?"
            params = (session_id,)
        query += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_workflow_insight(row) for row in rows]

    def list_unsynced_workflow_templates(
        self,
        session_id: str | None = None,
    ) -> list[WorkflowTemplate]:
        query = "SELECT * FROM workflow_templates WHERE synced = 0"
        params: tuple[object, ...] = ()
        if session_id:
            query += " AND session_id = ?"
            params = (session_id,)
        query += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_workflow_template(row) for row in rows]

    def list_unsynced_agent_handoff_drafts(
        self,
        session_id: str | None = None,
    ) -> list[AgentHandoffDraft]:
        query = "SELECT * FROM agent_handoff_queue WHERE synced = 0"
        params: tuple[object, ...] = ()
        if session_id:
            query += " AND session_id = ?"
            params = (session_id,)
        query += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_agent_handoff_draft(row) for row in rows]

    def list_unsynced_workflow_search_index_records(
        self,
        session_id: str | None = None,
    ) -> list[WorkflowSearchIndexRecord]:
        query = "SELECT * FROM workflow_search_index WHERE synced = 0"
        params: tuple[object, ...] = ()
        if session_id:
            query += " AND session_id = ?"
            params = (session_id,)
        query += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_workflow_search_index_record(row) for row in rows]

    def list_workflow_templates(self, limit: int = 20) -> list[WorkflowTemplate]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM workflow_templates
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_workflow_template(row) for row in rows]

    def list_workflow_templates_mine(self, user_id: str, limit: int = 20) -> list[WorkflowTemplate]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM workflow_templates
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._row_to_workflow_template(row) for row in rows]

    def list_workflow_templates_team(
        self,
        user_id: str | None,
        limit: int = 20,
    ) -> list[WorkflowTemplate]:
        with self._connect() as conn:
            if user_id:
                rows = conn.execute(
                    """
                    SELECT * FROM workflow_templates
                    WHERE visibility = 'team' OR user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM workflow_templates
                    WHERE visibility = 'team'
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [self._row_to_workflow_template(row) for row in rows]

    def search_workflow_templates(self, query: str, limit: int = 10) -> list[WorkflowTemplate]:
        pattern = f"%{query.lower()}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT wt.*
                FROM workflow_search_index wsi
                JOIN workflow_templates wt ON wt.id = wsi.template_id
                WHERE lower(wsi.searchable_text) LIKE ?
                ORDER BY wsi.created_at DESC
                LIMIT ?
                """,
                (pattern, limit),
            ).fetchall()
        return [self._row_to_workflow_template(row) for row in rows]

    def search_workflow_templates_mine(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
    ) -> list[WorkflowTemplate]:
        pattern = f"%{query.lower()}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT wt.*
                FROM workflow_search_index wsi
                JOIN workflow_templates wt ON wt.id = wsi.template_id
                WHERE lower(wsi.searchable_text) LIKE ?
                  AND wsi.user_id = ?
                ORDER BY wsi.created_at DESC
                LIMIT ?
                """,
                (pattern, user_id, limit),
            ).fetchall()
        return [self._row_to_workflow_template(row) for row in rows]

    def search_workflow_templates_team(
        self,
        query: str,
        user_id: str | None,
        limit: int = 10,
    ) -> list[WorkflowTemplate]:
        pattern = f"%{query.lower()}%"
        with self._connect() as conn:
            if user_id:
                rows = conn.execute(
                    """
                    SELECT wt.*
                    FROM workflow_search_index wsi
                    JOIN workflow_templates wt ON wt.id = wsi.template_id
                    WHERE lower(wsi.searchable_text) LIKE ?
                      AND (wsi.visibility = 'team' OR wsi.user_id = ?)
                    ORDER BY wsi.created_at DESC
                    LIMIT ?
                    """,
                    (pattern, user_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT wt.*
                    FROM workflow_search_index wsi
                    JOIN workflow_templates wt ON wt.id = wsi.template_id
                    WHERE lower(wsi.searchable_text) LIKE ?
                      AND wsi.visibility = 'team'
                    ORDER BY wsi.created_at DESC
                    LIMIT ?
                    """,
                    (pattern, limit),
                ).fetchall()
        return [self._row_to_workflow_template(row) for row in rows]

    def mark_session_synced(self, session_id: str, cloud_id: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET synced = 1, cloud_id = COALESCE(?, cloud_id) WHERE id = ?",
                (cloud_id, session_id),
            )

    def mark_chunk_summary_synced(self, summary_id: str, cloud_id: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE chunk_summaries
                SET synced = 1, cloud_id = COALESCE(?, cloud_id)
                WHERE id = ?
                """,
                (cloud_id, summary_id),
            )

    def mark_final_pseudocode_synced(self, final_id: str, cloud_id: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE final_pseudocode
                SET synced = 1, cloud_id = COALESCE(?, cloud_id)
                WHERE id = ?
                """,
                (cloud_id, final_id),
            )

    def mark_workflow_insight_synced(self, insight_id: str, cloud_id: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflow_insights
                SET synced = 1, cloud_id = COALESCE(?, cloud_id)
                WHERE id = ?
                """,
                (cloud_id, insight_id),
            )

    def mark_workflow_template_synced(self, template_id: str, cloud_id: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflow_templates
                SET synced = 1, cloud_id = COALESCE(?, cloud_id)
                WHERE id = ?
                """,
                (cloud_id, template_id),
            )

    def mark_agent_handoff_draft_synced(
        self,
        draft_id: str,
        cloud_id: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE agent_handoff_queue
                SET synced = 1, cloud_id = COALESCE(?, cloud_id)
                WHERE id = ?
                """,
                (cloud_id, draft_id),
            )

    def mark_workflow_search_index_record_synced(
        self,
        record_id: str,
        cloud_id: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflow_search_index
                SET synced = 1, cloud_id = COALESCE(?, cloud_id)
                WHERE id = ?
                """,
                (cloud_id, record_id),
            )

    def purge_expired_raw_data(self, session_id: str, cutoff: datetime) -> dict[str, int]:
        screenshot_paths = [
            Path(record.local_path)
            for record in self.get_screenshots(session_id)
            if record.captured_at <= cutoff
        ]
        audio_paths = [
            Path(event.metadata["path"])
            for event in self.get_events(session_id)
            if event.event_type == EventType.AUDIO_RECORDING
            and event.timestamp <= cutoff
            and event.metadata.get("path")
        ]

        with self._connect() as conn:
            screenshots_deleted = conn.execute(
                """
                DELETE FROM screenshots
                WHERE session_id = ? AND captured_at <= ?
                """,
                (session_id, cutoff.isoformat()),
            ).rowcount

            placeholders = ",".join("?" for _ in self.PURGEABLE_EVENT_TYPES)
            events_deleted = conn.execute(
                f"""
                DELETE FROM events
                WHERE session_id = ?
                  AND timestamp <= ?
                  AND event_type IN ({placeholders})
                """,
                (session_id, cutoff.isoformat(), *self.PURGEABLE_EVENT_TYPES),
            ).rowcount

        files_deleted = 0
        for path in [*screenshot_paths, *audio_paths]:
            try:
                if path.exists():
                    path.unlink()
                    files_deleted += 1
            except OSError:
                continue

        return {
            "screenshots_deleted": screenshots_deleted,
            "event_rows_deleted": events_deleted,
            "screenshot_files_deleted": files_deleted,
        }

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        return Session(
            id=row["id"],
            user_id=row["user_id"],
            visibility=row["visibility"],
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            session_name=row["session_name"],
            device_name=row["device_name"],
            os_name=row["os_name"],
            sync_enabled=bool(row["sync_enabled"]),
            status=row["status"],
            cloud_id=row["cloud_id"],
            synced=bool(row["synced"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_event(self, row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"],
            session_id=row["session_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            event_type=EventType(row["event_type"]),
            app_name=row["app_name"],
            window_title=row["window_title"],
            metadata=json.loads(row["metadata"]),
            synced=bool(row["synced"]),
            cloud_id=row["cloud_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_screenshot(self, row: sqlite3.Row) -> ScreenshotRecord:
        return ScreenshotRecord(
            id=row["id"],
            session_id=row["session_id"],
            event_id=row["event_id"],
            local_path=row["local_path"],
            storage_path=row["storage_path"],
            ocr_text=row["ocr_text"],
            captured_at=datetime.fromisoformat(row["captured_at"]),
            synced=bool(row["synced"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_chunk_summary(self, row: sqlite3.Row) -> ChunkSummary:
        return ChunkSummary(
            id=row["id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            chunk_index=row["chunk_index"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            summary=row["summary"],
            observed_apps=json.loads(row["observed_apps"]),
            confidence=row["confidence"],
            synced=bool(row["synced"]),
            cloud_id=row["cloud_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_final_pseudocode(self, row: sqlite3.Row) -> FinalPseudocode:
        return FinalPseudocode(
            id=row["id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            pseudocode=json.loads(row["pseudocode"]),
            plain_text=row["plain_text"],
            suggestions=json.loads(row["suggestions"]),
            synced=bool(row["synced"]),
            cloud_id=row["cloud_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_workflow_insight(self, row: sqlite3.Row) -> WorkflowInsight:
        return WorkflowInsight(
            id=row["id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            summary=row["summary"],
            main_apps=json.loads(row["main_apps"]),
            detected_task_type=row["detected_task_type"],
            tags=json.loads(row["tags"]),
            automation_score=row["automation_score"],
            automation_reason=row["automation_reason"],
            recommended_next_action=row["recommended_next_action"],
            synced=bool(row["synced"]),
            cloud_id=row["cloud_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_workflow_template(self, row: sqlite3.Row) -> WorkflowTemplate:
        return WorkflowTemplate(
            id=row["id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            title=row["title"],
            description=row["description"],
            category=row["category"],
            tags=json.loads(row["tags"]),
            pseudocode=json.loads(row["pseudocode"]),
            plain_text=row["plain_text"],
            visibility=row["visibility"],
            shared_with_team=bool(row["shared_with_team"]),
            created_from=row["created_from"],
            synced=bool(row["synced"]),
            cloud_id=row["cloud_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_agent_handoff_draft(self, row: sqlite3.Row) -> AgentHandoffDraft:
        return AgentHandoffDraft(
            id=row["id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            template_id=row["template_id"],
            status=row["status"],
            proposed_action=row["proposed_action"],
            action_plan=json.loads(row["action_plan"]),
            requires_user_approval=bool(row["requires_user_approval"]),
            synced=bool(row["synced"]),
            cloud_id=row["cloud_id"],
            approved_at=datetime.fromisoformat(row["approved_at"]) if row["approved_at"] else None,
            executed_at=datetime.fromisoformat(row["executed_at"]) if row["executed_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_workflow_search_index_record(
        self,
        row: sqlite3.Row,
    ) -> WorkflowSearchIndexRecord:
        return WorkflowSearchIndexRecord(
            id=row["id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            template_id=row["template_id"],
            searchable_text=row["searchable_text"],
            tags=json.loads(row["tags"]),
            visibility=row["visibility"],
            synced=bool(row["synced"]),
            cloud_id=row["cloud_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
