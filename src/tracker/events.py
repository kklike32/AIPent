from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class EventType(StrEnum):
    MOUSE_CLICK = "mouse_click"
    KEYBOARD_SHORTCUT = "keyboard_shortcut"
    SCREENSHOT = "screenshot"
    OCR_TEXT = "ocr_text"
    ACTIVE_WINDOW = "active_window"
    SESSION_START = "session_start"
    SESSION_STOP = "session_stop"


@dataclass(slots=True)
class Event:
    session_id: int
    event_type: EventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    app_name: str | None = None
    window_title: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    id: int | None = None

    def iso_timestamp(self) -> str:
        return self.timestamp.isoformat()
