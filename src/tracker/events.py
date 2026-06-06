from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    SESSION_START = "session_start"
    SESSION_STOP = "session_stop"
    MOUSE_CLICK = "mouse_click"
    KEYBOARD_KEY = "keyboard_key"
    KEYBOARD_SHORTCUT = "keyboard_shortcut"
    ACTIVE_WINDOW = "active_window"
    SCREENSHOT = "screenshot"
    OCR_TEXT = "ocr_text"
    PSEUDOCODE_GENERATED = "pseudocode_generated"
    SUGGESTION_GENERATED = "suggestion_generated"


def _uuid() -> str:
    return str(uuid4())


class Session(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str | None = None
    visibility: str = "private"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    session_name: str | None = None
    device_name: str | None = None
    os_name: str | None = None
    sync_enabled: bool = False
    status: str = "running"
    cloud_id: str | None = None
    synced: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Event(BaseModel):
    id: str = Field(default_factory=_uuid)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: EventType
    app_name: str | None = None
    window_title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    synced: bool = False
    cloud_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScreenshotRecord(BaseModel):
    id: str = Field(default_factory=_uuid)
    session_id: str
    event_id: str | None = None
    local_path: str
    storage_path: str | None = None
    ocr_text: str | None = None
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    synced: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class ActivityChunk:
    session_id: str
    chunk_index: int
    started_at: str
    ended_at: str
    screenshots: list[Path]
    mouse_events: list[dict]
    keyboard_shortcuts: list[dict]
    active_windows: list[dict]
    ocr_text: list[str]


@dataclass(slots=True)
class ChunkSummary:
    session_id: str
    chunk_index: int
    started_at: str
    ended_at: str
    summary: str
    observed_apps: list[str]
    confidence: str
    user_id: str | None = None
    id: str = field(default_factory=_uuid)
    synced: bool = False
    cloud_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class FinalPseudocode:
    session_id: str
    pseudocode: list[str]
    plain_text: str
    suggestions: list[str]
    user_id: str | None = None
    id: str = field(default_factory=_uuid)
    synced: bool = False
    cloud_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class WorkflowInsight:
    session_id: str
    summary: str
    main_apps: list[str]
    detected_task_type: str
    tags: list[str]
    automation_score: int
    automation_reason: str
    recommended_next_action: str
    user_id: str | None = None
    id: str = field(default_factory=_uuid)
    synced: bool = False
    cloud_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class WorkflowTemplate:
    session_id: str
    title: str
    description: str
    category: str
    tags: list[str]
    pseudocode: list[str]
    plain_text: str
    user_id: str | None = None
    visibility: str = "private"
    shared_with_team: bool = False
    created_from: str = "session_summary"
    id: str = field(default_factory=_uuid)
    synced: bool = False
    cloud_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class AgentHandoffDraft:
    session_id: str
    template_id: str | None
    status: str
    proposed_action: str
    action_plan: list[str]
    requires_user_approval: bool = True
    user_id: str | None = None
    id: str = field(default_factory=_uuid)
    synced: bool = False
    cloud_id: str | None = None
    approved_at: datetime | None = None
    executed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class WorkflowSearchIndexRecord:
    session_id: str
    template_id: str | None
    searchable_text: str
    tags: list[str]
    user_id: str | None = None
    visibility: str = "private"
    id: str = field(default_factory=_uuid)
    synced: bool = False
    cloud_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
